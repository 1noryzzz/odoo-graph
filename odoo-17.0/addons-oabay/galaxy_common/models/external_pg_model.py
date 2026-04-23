# -*- coding: utf-8 -*-

import logging
import re

from decimal import *
from odoo import _, api, models, fields
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError
from odoo.tools import partition, Query, OrderedSet

_logger = logging.getLogger(__name__)


class MySqlModel(models.AbstractModel):
    _name = 'expg.model.mixin'
    _description = '外部PG库数据源'
    
    _external_db_source = False
    
    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if not self._external_db_source:
            raise ValidationError(_(u'外部数据源未设置'))
        
        # model = self.with_user(access_rights_uid) if access_rights_uid else self
        # model.check_access_rights('read')

        if expression.is_false(self, domain):
            # optimization: no need to query, as no record satisfies the domain
            return 0 if count else []

        # the flush must be done before the _where_calc(), as the latter can do some selects
        self._flush_search(domain, order=order)

        query = self._where_calc(domain)
        self._apply_ir_rules(query, 'read')
        query.limit = limit

        pg_dbs = self.env['base.external.dbsource'].search(
            [('name', '=', self._external_db_source)])
        with pg_dbs.connection_open() as db:
            if count:
                # Ignore order and offset when just counting, they don't make sense and could
                # hurt performance
                if limit:
                    # Special case to avoid counting every record in DB (which can be really slow).
                    # The result will be between 0 and limit.
                    query_str, params = query.select("")  # generates a `SELECT FROM` (faster)
                    query_str = f"SELECT COUNT(*) FROM ({query_str}) t"
                else:
                    query_str, params = query.select("COUNT(*)")

                return db.query(query_str, **params)[0][0]

            query.order = self._generate_order_by(order, query).replace('ORDER BY ', '')
            query.offset = offset

            query_str, params = query.select("id")
            return [row[0] for row in db.query(query_str, **{})]

    def _read(self, field_names):
        """ Read the given fields of the records in ``self`` from the database,
            and store them in cache. Skip fields that are not stored.

            :param field_names: list of field names to read
        """
        if not self._external_db_source:
            raise ValidationError(_(u'外部数据源未设置'))

        if not self:
            return
        self.check_access_rights('read')

        # determine columns fields and those with their own read() method
        column_fields = []
        other_fields = []
        translated_field_names = []
        for name in field_names:
            if name == 'id':
                continue
            field = self._fields.get(name)
            if not field:
                _logger.warning("%s._read() with unknown field %r", self._name, name)
                continue
            if field.base_field.store and field.base_field.column_type:
                column_fields.append(field)
            elif field.store and not field.column_type:
                # non-column fields: for the sake of simplicity, we ignore inherited fields
                other_fields.append(field)
            if field.store and field.translate:
                translated_field_names.append(field.name)

            if field.type == 'properties':
                # force calling fields.read for properties field because
                # we want to read all relational properties in batch
                # (and check their existence in batch as well)
                other_fields.append(field)

        if column_fields:
            cr, context = self.env.cr, self.env.context

            # If a read() follows a write(), we must flush the updates that have
            # an impact on checking security rules, as they are injected into
            # the query.  However, we don't need to flush the fields to fetch,
            # as explained below when putting values in cache.

            # Since only one language translation is fetched from database,
            # we must flush these translated fields before read
            # E.g. in database, the {'en_US': 'English'},
            # write record.with_context(lang='en_US').name = 'English2'
            # then record.with_context(lang='fr_FR').name => cache miss => _read
            # 'English2'should is flushed before query as it is the fallback of empty 'fr_FR'
            if translated_field_names:
                self.flush_recordset(translated_field_names)
            self._flush_search([], order='id')

            # make a query object for selecting ids, and apply security rules to it
            query = Query(cr, self._table, self._table_query)
            self._apply_ir_rules(query, 'read')

            # the query may involve several tables: we need fully-qualified names
            def qualify(field):
                qname = self._inherits_join_calc(self._table, field.name, query)
                if field.type == 'binary' and (
                        context.get('bin_size') or context.get('bin_size_' + field.name)):
                    # PG 9.2 introduces conflicting pg_size_pretty(numeric) -> need ::cast
                    qname = f'pg_size_pretty(length({qname})::bigint)'
                return f'{qname} AS "{field.name}"'

            # selected fields are: 'id' followed by column_fields
            qual_names = [qualify(field) for field in [self._fields['id']] + column_fields]

            # determine the actual query to execute (last parameter is added below)
            query.add_where(f'"{self._table}".id IN %s')
            query_str, params = query.select(*qual_names)
            
            result = []
            pg_dbs = self.env['base.external.dbsource'].search(
                [('name', '=', self._external_db_source)])
            with pg_dbs.connection_open() as db:
                for sub_ids in cr.split_for_in_conditions(self.ids):
                    rs = db.query(query_str, **{'ids': sub_ids})
                    #cr.execute(query_str, params + [sub_ids])
                    result += rs
        else:
            self.check_access_rule('read')
            result = [(id_,) for id_ in self.ids]

        fetched = self.browse()
        if result:
            # result = [(id1, a1, b1), (id2, a2, b2), ...]
            # column_values = [(id1, id2, ...), (a1, a2, ...), (b1, b2, ...)]
            column_values = zip(*result)
            ids = next(column_values)
            fetched = self.browse(ids)

            # If we assume that the value of a pending update is in cache, we
            # can avoid flushing pending updates if the fetched values do not
            # overwrite values in cache.
            for field in column_fields:
                values = next(column_values)
                # store values in cache, but without overwriting
                self.env.cache.insert_missing(fetched, field, values)

            # process non-column fields
            for field in other_fields:
                field.read(fetched)

        # possibly raise exception for the records that could not be read
        missing = self - fetched
        if missing:
            extras = fetched - self
            if extras:
                raise AccessError(_(
                    "Database fetch misses ids (%(missing)s) and has extra ids (%(extra)s),"
                    " may be caused by a type incoherence in a previous request",
                    missing=missing._ids,
                    extra=extras._ids,
                ))
            # mark non-existing records in missing
            forbidden = missing.exists()
            if forbidden:
                raise self.env['ir.rule']._make_access_error('read', forbidden)

    @api.returns('self')
    def exists(self):
        """  exists() -> records

        Returns the subset of records in ``self`` that exist.
        It can be used as a test on records::

            if record.exists():
                ...

        By convention, new records are returned as existing.
        """
        if not self._external_db_source:
            raise ValidationError(_(u'外部数据源未设置'))

        new_ids, ids = partition(lambda i: isinstance(i, models.NewId), self._ids)
        if not ids:
            return self
        query = Query(self.env.cr, self._table, self._table_query)
        query.add_where(f'"{self._table}".id IN %s', [tuple(ids)])
        query_str, params = query.select()
        
        mysql_dbs = self.env['base.external.dbsource'].search(
            [('name', '=', self._external_db_source)])
        with mysql_dbs.connection_open() as db:
            valid_ids = set([row[0]
                            for row in db.query(query_str, **params)] + new_ids)
            return self.browse(i for i in self._ids if i in valid_ids)

# keep those imports here to avoid dependency cycle errors
# pylint: disable=wrong-import-position
from odoo.osv import expression
