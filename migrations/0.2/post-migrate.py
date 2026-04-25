# -*- coding: utf-8 -*-
"""
Migration 0.1 -> 0.2
Conversion du champ remarque_generale de Text vers Html.
Les sauts de ligne sont convertis en <br/> et les caractères spéciaux HTML échappés.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE is_consigne_journaliere
        SET remarque_generale =
            '<p>' ||
            replace(
                replace(
                    replace(
                        replace(remarque_generale, '&', '&amp;'),
                        '<', '&lt;'
                    ),
                    '>', '&gt;'
                ),
                E'\\n', '<br/>'
            ) ||
            '</p>'
        WHERE remarque_generale IS NOT NULL
          AND remarque_generale != ''
    """)
