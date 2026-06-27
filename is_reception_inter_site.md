# is.reception.inter.site — Documentation et analyse

## Vue d'ensemble

Le modèle `is.reception.inter.site` gère les réceptions de marchandises inter-sites. Il orchestre le lien entre les bons de commande fournisseur (purchase.order), les réceptions Odoo (stock.picking) et les unités de colisage (is.galia.base.uc / is.galia.base.um).

---

## Création d'une réception

Les pickings (`stock.picking`) sont créés **avant** la validation, soit :
- lors de la confirmation d'un bon de commande fournisseur (flux standard Odoo)
- par `dupliquer_reception_test_action` pour les tests (copie d'un BC existant)
- via l'import inter-bases (copie de la base de production vers la base de test)

À ce stade, les pickings n'ont **pas encore de lots** (`stock.lot`) ni de lignes de mouvement (`stock.move.line`).

---

## Validation — `valider_receptions_action`

C'est ici que les **lots sont créés** et que les `stock.move.line` sont générées.

La méthode itère sur tous les pickings liés à la réception et, pour chaque picking non encore validé, choisit entre deux chemins :

### Chemin 1 — Avec UC (is.galia.base.uc)

**Condition** : des UC existent, liées au move (`stock_move_rcp_id`) et à la réception (`reception_inter_site_id`).

**Méthode** : `_valider_picking_par_lot_fournisseur(obj, picking, qt_by_product_production, productions)`

**Fonctionnement** :
1. Pour chaque move du picking, les UC associées sont récupérées.
2. Les UC portent un champ `production` = numéro de lot fournisseur (ex: `OF53973`).
3. Une liste `productions` est construite (un élément par lot fournisseur distinct).
4. **La liste est triée** (`productions.sort()`) pour garantir l'ordre alphabétique/numérique croissant.
5. Pour chaque production (lot fournisseur) dans l'ordre :
   - Un lot Odoo est créé (nom = `AAMMJJ + nom picking`), avec `is_lot_fournisseur = production`
   - Une `stock.move.line` est créée avec `qty_done` = quantité des UC
   - Le picking est validé (`_action_done()`)
   - Un reliquat (backorder) est créé automatiquement pour les productions suivantes
   - Le backorder devient le `current_picking` pour l'itération suivante

**Résultat** : chaque picking (original + reliquats) reçoit un lot fournisseur dans l'ordre trié. Le premier picking (numéro de réception le plus petit) reçoit le plus petit numéro de lot fournisseur.

### Chemin 2 — Sans UC (stock.transfer_details)

**Condition** : aucune UC trouvée pour le picking.

**Méthode** : wizard `stock.transfer_details`

**Fonctionnement** :
1. `_default_get_line_ids` crée une ligne par move du picking.
2. Un lot est créé ou trouvé avec le nom `AAMMJJ + nom_picking`.
3. La quantité est forcée à `picking.is_qt_livree_inter_site` (quantité totale livrée).
4. `valider_action()` crée la `stock.move.line` et valide le picking.
5. Si `qty_done < product_uom_qty`, Odoo crée un reliquat.

**Limitation** : pas de mécanisme de tri des lots fournisseur dans ce chemin. Le champ `is_lot_fournisseur` n'est positionné que si `line.is_lot_fournisseur` est renseigné manuellement (via l'UI du wizard), ce qui n'est pas le cas en appel automatique.

---

## Problème d'ordre des lots fournisseur

### Symptôme

Pour un produit avec plusieurs lots fournisseur, le numéro de réception (R-213130, R-213153, R-213154) ne correspond pas à l'ordre trié des lots fournisseur (OF53706, OF53972, OF53973) :

| Picking | Numéro de lot fournisseur | Attendu (trié) |
|---------|--------------------------|----------------|
| R-213130 | OF53973 | OF53706 |
| R-213153 | OF53972 | OF53972 |
| R-213154 | OF53706 | OF53973 |

### Cause

Dans le chemin UC, la liste `productions` était construite dans l'ordre d'apparition des UC en base (ordre de création/scan), sans tri. Le premier picking recevait donc le premier lot scanné, pas le plus petit.

### Correction appliquée

Dans `valider_receptions_action` ([is_reception_inter_site.py](models/is_reception_inter_site.py) ligne ~667) :

```python
if productions:
    productions.sort()   # ← tri ajouté
    self._valider_picking_par_lot_fournisseur(...)
```

### Réception 647 — contexte des tests

La réception 647 a été créée par `dupliquer_reception_test_action` à partir de données de production (copie inter-bases). Les lots ont été créés lors de la validation de cette réception (pas à la création), via le chemin **sans UC** (`stock.transfer_details`). L'ordre incorrect des lots reflète l'état de la base de production avant l'application du correctif.

Le correctif `productions.sort()` s'applique au chemin **avec UC** (flux de production réel). Pour le chemin sans UC, le tri des lots n'est pas encore implémenté car `is_lot_fournisseur` n'est pas connu au moment de la validation dans ce chemin.

---

## Champs clés

| Modèle | Champ | Rôle |
|--------|-------|------|
| `is.galia.base.uc` | `production` | Numéro de lot fournisseur (ex: OF53973) |
| `stock.lot` | `is_lot_fournisseur` | Numéro de lot fournisseur stocké sur le lot Odoo |
| `stock.move.line` | `is_lot_fournisseur` | Champ related → `lot_id.is_lot_fournisseur` |
| `stock.picking` | `is_qt_livree_inter_site` | Quantité totale livrée (toutes tranches) |
| `stock.picking` | `is_reception_inter_site_id` | Lien vers la réception inter-site |
