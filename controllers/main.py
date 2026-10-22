import json
from odoo import http                     # type: ignore
from odoo.http import request             # type: ignore
from werkzeug.exceptions import NotFound  # type: ignore

class SignupDisabled(http.Controller):

    @http.route('/web/signup', type='http', auth='public', website=True)
    def disable_signup(self, **kwargs):
        # Option 1 : renvoyer une erreur 404
        raise NotFound()

        # Option 2 : rediriger vers la page de login
        # return request.redirect('/web/login')


class ApplicationWeb(http.Controller):
    # Manifest d'application web (absent d'Odoo 16) pour installer Odoo en plein écran depuis Chrome (Zebra TC22)

    @http.route('/is_plastigray16/manifest.webmanifest', type='http', auth='none', methods=['GET'])
    def manifest(self):
        # auth='none' : Chrome peut lire le manifest sans session (pas de base nécessaire)
        manifest = {
            'name'            : "Odoo Plastigray",
            'short_name'      : "Odoo PG",
            'start_url'       : '/is_plastigray16/start',
            'scope'           : '/',
            'display'         : 'standalone',
            'background_color': '#ffffff',
            'theme_color'     : '#714B67',
            # Logo Plastigray (carré, la plus grande icône sert à l'écran de démarrage de l'application installée)
            'icons': [
                {'src': '/is_plastigray16/static/src/img/plastigray-192.png', 'sizes': '192x192', 'type': 'image/png'},
                {'src': '/is_plastigray16/static/src/img/plastigray-512.png', 'sizes': '512x512', 'type': 'image/png'},
            ],
        }
        return request.make_response(json.dumps(manifest), headers=[
            ('Content-Type' , 'application/manifest+json'),
            ('Cache-Control', 'no-cache'),
        ])


    @http.route('/is_plastigray16/start', type='http', auth='user', methods=['GET'])
    def start(self):
        # Page de départ de l'application installée : liste des contrôles qualité
        action = request.env.ref('is_plastigray16.is_controle_qualite_um_action')
        return request.redirect('/web#action=%s'%action.id)
