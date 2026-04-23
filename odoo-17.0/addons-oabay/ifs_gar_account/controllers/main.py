from odoo.http import Controller, request, route
from odoo.addons.bus.controllers.main import BusController

class Controller(BusController):
    
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            registry, cr, uid, context = request.registry, request.cr, request.session.uid, request.context
            registry.get('im_chat.presence').update(cr, uid, options.get('im_presence', False), context=context)
            # channel to receive message
            channels.append((request.db,'im_chat.session', request.uid))
        return super(Controller, self)._poll(dbname, channels, last, options)