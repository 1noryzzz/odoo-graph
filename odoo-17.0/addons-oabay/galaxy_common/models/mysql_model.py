# -*- coding: utf-8 -*-

import logging
import re

from decimal import *
from odoo import _, api, models, fields
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError

from odoo.tools import Query, OrderedSet

_logger = logging.getLogger(__name__)


class MySqlModel(models.AbstractModel):
    _name = 'mysql.model.mixin'
    _description = '适配 Mysql'

    _id_field_name = False
    _id_field_type = False
    _replace_table_alias = {}
    _date_add_fields = {}
    _view_sql = False

    # @classmethod
    # def _browse(cls, env, ids, prefetch_ids):
    #     """ Create a recordset instance.

    #     :param env: an environment
    #     :param ids: a tuple of record ids
    #     :param prefetch_ids: a collection of record ids (for prefetching)
    #     """
    #     records = object.__new__(cls)
    #     records.env = env
    #     records._ids = ids
    #     records._prefetch_ids = prefetch_ids
    #     if len(ids) > 0 and records._id_field_name:
    #         records._fields['id'].type = records._id_field_type
    #     return records

    id = fields.Id(automatic=True)

    def _mysql_table_with_int_id(self, alias):
        return '''
            (SELECT @rownum:=@rownum+1 AS id, %s.*
            FROM %s, (SELECT @rownum:=0) %s) %s
        ''' % (self._table, self._table, self._table, alias)

    def _mysql_grammar_parse(self, where_clauses, where_params):
        new_where_clauses = []
        new_params = {}

        p_index = 0
        for clause in where_clauses:
            new_where_clause = clause.replace('"', '`').replace(
                '::text', '').replace('ilike', 'like')

            start_index = 0  # 把查询条件分段，以判断当前这个参数，是哪个查询条件的，方便对查询值做处理
            p_count = re.split(r'[\s\.\(\)\",]+', clause).count('%s')
            while p_count > 0:
                param_index = ':p_%d' % p_index
                new_where_clause = new_where_clause.replace(
                    '%s', param_index, 1)
                new_params['p_%d' % p_index] = where_params[p_index]

                param_region = new_where_clause[start_index: new_where_clause.index(
                    param_index)]
                start_index = new_where_clause.index(
                    param_index) + len(param_index)
                for key, value in self._date_add_fields.items():
                    if key in param_region:
                        new_where_clause = new_where_clause.replace(
                            param_index, 'DATE_ADD(%s, INTERVAL + %d HOUR)' % (param_index, value))

                p_index += 1
                p_count -= 1

            for key, value in self._replace_table_alias.items():
                new_where_clause = new_where_clause.replace(key, value)

            new_where_clauses.append(new_where_clause)

        return new_where_clauses, new_params

    def _mysql_select(self, query, *args):
        """ Return the SELECT query as a pair ``(query_string, query_params)``. """
        from_clause, where_clause, params = query.get_sql()
        query_str = 'SELECT {} FROM {} {}{}{}'.format(
            ", ".join(
                args or ['%s.%s' % (self._table, self._id_field_name or 'id')]),
            (self._view_sql % {
                'where': 'WHERE %s' % (where_clause or "TRUE")
            }) if self._view_sql else (
                '%(table)s WHERE %(where)s' % {
                    'table': from_clause.replace('"', '`'),
                    'where': where_clause or "TRUE"
                }
            ),
            (" ORDER BY %s" % query.order.replace(
                '."id"', '."%s"' % (self._id_field_name or 'id')).replace('"', '`')) if query.order else "",
            (" LIMIT %d" % query.limit) if query.limit else "",
            (" OFFSET %d" % query.offset) if query.offset else "",
        )
        return query_str, params

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if not self._external_db_source:
            raise ValidationError(_(u'外部数据源未设置'))

        model = self.with_user(
            access_rights_uid) if access_rights_uid else self
        model.check_access_rights('read')

        if expression.is_false(self, args):
            # optimization: no need to query, as no record satisfies the domain
            return 0 if count else []

        # the flush must be done before the _where_calc(), as the latter can do some selects
        self._flush_search(args, order=order)

        query = self._where_calc(args)
        new_where_clauses, new_params = self._mysql_grammar_parse(
            query._where_clauses, query._where_params)
        query._where_clauses = new_where_clauses
        self._apply_ir_rules(query, 'read')

        mysql_dbs = self.env['base.external.dbsource'].search(
            [('name', '=', self._external_db_source)])
        with mysql_dbs.connection_open() as db:
            if count:
                # Ignore order, limit and offset when just counting, they don't make sense and could
                # hurt performance
                query_str, params = self._mysql_select(query, "count(1)")
                return db.query(query_str, **new_params)[0][0]

            query.order = self._generate_order_by(
                order, query).replace('ORDER BY ', '')
            query.limit = limit
            query.offset = offset

            query_str, params = self._mysql_select(query)
            return [row[0] for row in db.query(query_str, **new_params)]

    # 这个方法需要重新实现
    # def _read(self, fields):
    #     """ Read the given fields of the records in ``self`` from the database,
    #         and store them in cache. Access errors are also stored in cache.
    #         Skip fields that are not stored.

    #         :param field_names: list of column names of model ``self``; all those
    #             fields are guaranteed to be read
    #         :param inherited_field_names: list of column names from parent
    #             models; some of those fields may not be read
    #     """
    #     if not self._external_db_source:
    #         raise ValidationError(_(u'外部数据源未设置'))

    #     if not self:
    #         return
    #     self.check_access_rights('read')

    #     # if a read() follows a write(), we must flush updates, as read() will
    #     # fetch from database and overwrites the cache (`test_update_with_id`)
    #     self.flush(fields, self)

    #     field_names = []
    #     inherited_field_names = []
    #     for name in fields:
    #         field = self._fields.get(name)
    #         if field:
    #             if field.store:
    #                 field_names.append(name)
    #             elif field.base_field.store:
    #                 inherited_field_names.append(name)
    #         else:
    #             _logger.warning(
    #                 "%s.read() with unknown field '%s'", self._name, name)

    #     # determine the fields that are stored as columns in tables; ignore 'id'
    #     fields_pre = [
    #         field
    #         for field in (self._fields[name] for name in field_names + inherited_field_names)
    #         if field.name != 'id'
    #         if field.base_field.store and field.base_field.column_type
    #         if not (field.inherited and callable(field.base_field.translate))
    #     ]

    #     if fields_pre:
    #         env = self.env
    #         cr, user, context, su = env.args

    #         # make a query object for selecting ids, and apply security rules to it
    #         query = Query(self.env.cr, self._table, self._table_query)
    #         self._apply_ir_rules(query, 'read')

    #         # the query may involve several tables: we need fully-qualified names
    #         def qualify(field):
    #             col = field.name
    #             if col == 'id' and self._id_field_name:
    #                 t_col = self._id_field_name
    #                 # field.type = self._id_field_type
    #             else:
    #                 t_col = col
    #             res = self._inherits_join_calc(
    #                 self._table, t_col, query).replace('"', '`')
    #             if field.type == 'binary' and (context.get('bin_size') or context.get('bin_size_' + col)):
    #                 # PG 9.2 introduces conflicting pg_size_pretty(numeric) -> need ::cast
    #                 res = 'pg_size_pretty(length(%s)::bigint)' % res
    #             return '%s as `%s`' % (res, col)

    #         def float_ignore_none(val):
    #             return float(val) if val else float(0.000)

    #         # selected fields are: 'id' followed by fields_pre
    #         qual_names = [qualify(name)
    #                       for name in [self._fields['id']] + fields_pre]

    #         # determine the actual query to execute (last parameter is added below)
    #         query.add_where('%s.%s IN :ids' %
    #                         (self._table, self._id_field_name or 'id'))
    #         query_str, params = self._mysql_select(query, *qual_names)

    #         result = []
    #         mysql_dbs = self.env['base.external.dbsource'].search(
    #             [('name', '=', self._external_db_source)])
    #         with mysql_dbs.connection_open() as db:
    #             for sub_ids in cr.split_for_in_conditions(self.ids):
    #                 rs = db.query(query_str, **{'ids': sub_ids})
    #                 #cr.execute(query_str, params + [sub_ids])
    #                 result += rs

    #     else:
    #         self.check_access_rule('read')
    #         result = [(id_,) for id_ in self.ids]

    #     fetched = self.browse()
    #     if result:
    #         cols = zip(*result)
    #         ids = next(cols)
    #         fetched = self.browse(ids)

    #         for field in fields_pre:
    #             values = next(cols)

    #             # mysql查出来的是Decimal类型，需要转成float
    #             if values and field.type in ('float', 'monetary'):
    #                 values = tuple(map(float_ignore_none, values))

    #             if context.get('lang') and not field.inherited and callable(field.translate):
    #                 translate = field.get_trans_func(fetched)
    #                 values = list(values)
    #                 for index in range(len(ids)):
    #                     values[index] = translate(ids[index], values[index])

    #             # store values in cache
    #             self.env.cache.update(fetched, field, values)

    #         # determine the fields that must be processed now;
    #         # for the sake of simplicity, we ignore inherited fields
    #         for name in field_names:
    #             field = self._fields[name]
    #             if not field.column_type:
    #                 field.read(fetched)
    #             if field.deprecated:
    #                 _logger.warning('Field %s is deprecated: %s',
    #                                 field, field.deprecated)

    #     # possibly raise exception for the records that could not be read
    #     missing = self - fetched
    #     if missing:
    #         extras = fetched - self
    #         if extras:
    #             raise AccessError(
    #                 _("Database fetch misses ids ({}) and has extra ids ({}), may be caused by a type incoherence in a previous request").format(
    #                     missing._ids, extras._ids,
    #                 ))
    #         # mark non-existing records in missing
    #         forbidden = missing.exists()
    #         if forbidden:
    #             raise self.env['ir.rule']._make_access_error('read', forbidden)

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if not self._external_db_source:
            raise ValidationError(_(u'外部数据源未设置'))

        self.check_access_rights('read')
        query = self._where_calc(domain)
        fields = fields or [f.name for f in self._fields.values() if f.store]

        groupby = [groupby] if isinstance(
            groupby, str) else list(OrderedSet(groupby))
        groupby_list = groupby[:1] if lazy else groupby
        annotated_groupbys = [self._read_group_process_groupby(
            gb, query) for gb in groupby_list]
        groupby_fields = [g['field'] for g in annotated_groupbys]
        order = orderby or ','.join([g for g in groupby_list])
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}

        self._apply_ir_rules(query, 'read')
        for gb in groupby_fields:
            assert gb in self._fields, "Unknown field %r in 'groupby'" % gb
            gb_field = self._fields[gb].base_field
            assert gb_field.store and gb_field.column_type, "Fields in 'groupby' must be regular database-persisted fields (no function or related fields), or function fields with store=True"

        aggregated_fields = []
        select_terms = []
        fnames = []                     # list of fields to flush

        for fspec in fields:
            if fspec == 'sequence':
                continue
            if fspec == '__count':
                # the web client sometimes adds this pseudo-field in the list
                continue

            match = models.regex_field_agg.match(fspec)
            if not match:
                raise UserError(_("Invalid field specification %r.", fspec))

            name, func, fname = match.groups()
            if func:
                # we have either 'name:func' or 'name:func(fname)'
                fname = fname or name
                field = self._fields.get(fname)
                if not field:
                    raise ValueError(
                        "Invalid field %r on model %r" % (fname, self._name))
                if not (field.base_field.store and field.base_field.column_type):
                    raise UserError(_("Cannot aggregate field %r.", fname))
                if func not in models.VALID_AGGREGATE_FUNCTIONS:
                    raise UserError(
                        _("Invalid aggregation function %r.", func))
            else:
                # we have 'name', retrieve the aggregator on the field
                field = self._fields.get(name)
                if not field:
                    raise ValueError(
                        "Invalid field %r on model %r" % (name, self._name))
                if not (field.base_field.store and
                        field.base_field.column_type and field.group_operator):
                    continue
                func, fname = field.group_operator, name

            fnames.append(fname)

            if fname in groupby_fields:
                continue
            if name in aggregated_fields:
                raise UserError(_("Output name %r is used twice.", name))
            aggregated_fields.append(name)

            expr = self._inherits_join_calc(self._table, fname, query)
            if func.lower() == 'count_distinct':
                term = 'COUNT(DISTINCT %s) AS %s' % (expr, name)
            else:
                term = '%s(%s) AS %s' % (func, expr, name)
            select_terms.append(term)

        for gb in annotated_groupbys:
            select_terms.append('%s as %s ' %
                                (gb['qualified_field'], gb['groupby']))

        self._flush_search(domain, fields=fnames + groupby_fields)

        groupby_terms, orderby_terms = self._read_group_prepare(
            order, aggregated_fields, annotated_groupbys, query)

        new_where_clauses, new_params = self._mysql_grammar_parse(
            query._where_clauses, query._where_params)
        query._where_clauses = new_where_clauses

        from_clause, where_clause, where_clause_params = query.get_sql()
        if lazy and (len(groupby_fields) >= 2 or not self._context.get('group_by_no_leaf')):
            count_field = groupby_fields[0] if len(
                groupby_fields) >= 1 else '_'
        else:
            count_field = '_'
        count_field += '_count'

        def prefix_terms(prefix, terms): return (
            prefix + " " + ",".join([term.replace('"', '`') for term in terms])) if terms else ''

        def prefix_term(prefix, term): return ('%s %s' %
                                               (prefix, term)) if term else ''

        query = """
            SELECT min(%(table)s.%(id_field)s) AS id, count(%(table)s.%(id_field)s) AS %(count_field)s %(extra_fields)s
            FROM %(from)s
            %(groupby)s
            %(orderby)s
            %(limit)s
            %(offset)s
        """ % {
            'table': self._table,
            'id_field': self._id_field_name or 'id',
            'count_field': count_field,
            'extra_fields': prefix_terms(',', select_terms),
            'from': self._view_sql % {
                'where': prefix_term('WHERE', where_clause),
            } if self._view_sql else '%(from)s %(where)s' % {
                'from': from_clause.replace('"', '`'),
                'where': prefix_term('WHERE', where_clause),
            },
            'groupby': prefix_terms('GROUP BY', groupby_terms),
            'orderby': prefix_terms('ORDER BY', orderby_terms),
            'limit': prefix_term('LIMIT', int(limit) if limit else None),
            'offset': prefix_term('OFFSET', int(offset) if limit else None),
        }

        def float_ignore_none(val):
            for key, value in val.items():
                if isinstance(value, Decimal):
                    val[key] = float(value) if value else float(0.000)
            return val

        mysql_dbs = self.env['base.external.dbsource'].search(
            [('name', '=', self._external_db_source)])
        with mysql_dbs.connection_open() as db:
            fetched_data = tuple(
                map(float_ignore_none, db.query(query, **new_params).as_dict()))
        #self._cr.execute(query, where_clause_params)
        #fetched_data = self._cr.dictfetchall()

        if not groupby_fields:
            return fetched_data

        self._read_group_resolve_many2x_fields(
            fetched_data, annotated_groupbys)

        data = [{k: self._read_group_prepare_data(
            k, v, groupby_dict) for k, v in r.items()} for r in fetched_data]

        if self.env.context.get('fill_temporal') and data:
            data = self._read_group_fill_temporal(data, groupby, aggregated_fields,
                                                  annotated_groupbys)

        result = [self._read_group_format_result(
            d, annotated_groupbys, groupby, domain) for d in data]

        if lazy:
            # Right now, read_group only fill results in lazy mode (by default).
            # If you need to have the empty groups in 'eager' mode, then the
            # method _read_group_fill_results need to be completely reimplemented
            # in a sane way
            result = self._read_group_fill_results(
                domain, groupby_fields[0], groupby[len(annotated_groupbys):],
                aggregated_fields, count_field, result, read_group_order=order,
            )
        return result

    # @api.model
    # def fields_get(self, allfields=None, attributes=None):
    #     if self._id_field_name and self._id_field_type:
    #         self._fields['id'].type = self._id_field_type
    #     return super(MySqlModel, self).fields_get(allfields, attributes)

    @api.returns('self')
    def exists(self):
        if not self._external_db_source:
            raise ValidationError(_(u'外部数据源未设置'))

        """  exists() -> records

        Returns the subset of records in ``self`` that exist, and marks deleted
        records as such in cache. It can be used as a test on records::

            if record.exists():
                ...

        By convention, new records are returned as existing.
        """
        ids, new_ids = [], []
        for i in self._ids:
            (new_ids if isinstance(i, models.NewId) else ids).append(i)
        if not ids:
            return self

        where_clause = []
        params = {}
        p_index = 0
        for id in ids:
            where_clause.append(':p_%d' % p_index)
            params['p_%d' % p_index] = id
            p_index += 1

        query = 'SELECT {} FROM {}'.format(
            '%s.%s' % (self._table, self._id_field_name or 'id'),
            (self._view_sql % {
                'where': 'WHERE %(table)s.%(id)s IN (%(ids)s)' % {
                    'table': self._table,
                    'id': self._id_field_name or 'id',
                    'ids': ','.join(where_clause)}
            }) if self._view_sql else (
                '%(table)s WHERE %(table)s.%(id)s IN (%(ids)s)' % {
                    'table': self._table,
                    'id': self._id_field_name or 'id',
                    'ids': ','.join(where_clause)
                }
            )
        )

        mysql_dbs = self.env['base.external.dbsource'].search(
            [('name', '=', self._external_db_source)])
        with mysql_dbs.connection_open() as db:
            valid_ids = set([row[0]
                            for row in db.query(query, **params)] + new_ids)
            return self.browse(i for i in self._ids if i in valid_ids)


# keep those imports here to avoid dependency cycle errors
from odoo.osv import expression
