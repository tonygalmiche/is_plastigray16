#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyseur de logs Odoo - Performance des web_search_read
Synthèse par adresse IP, modèle et temps d'exécution

Format du log Odoo werkzeug:
"POST /web/dataset/call_kw/is.presse.cycle/web_search_read HTTP/1.0" 200 - 5 6.653 0.008
                                                                        ^^^ ^ ^^^^^^ ^^^^^
                                                    status_code --------+   |  |      +---- remaining_time (s hors SQL)
                                              content_length ----------+   |  +------------ query_time (s SQL)
                                                  query_count ----------+   +-------------- nombre requêtes SQL

Signification des chiffres:
- 5 = nombre de requêtes SQL exécutées
- 6.653 = temps total passé à exécuter les requêtes SQL (en secondes)
- 0.008 = temps hors SQL (traitement Python, etc.)
"""

import re
import sys
from collections import defaultdict
from pathlib import Path


class LogAnalyzer:
    """Analyser les logs Odoo werkzeug pour les performances"""
    
    # Regex pour parser une ligne de log werkzeug
    LOG_PATTERN = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+.*?INFO\s+(\S+)\s+werkzeug:.*?'
        r'(\d+\.\d+\.\d+\.\d+)\s+-\s+-\s+\[.*?\]\s+"'
        r'(GET|POST|PUT|DELETE)\s+(.*?)\s+HTTP'
        r'.*?"\s+(\d+)\s+(-|\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)'
    )
    
    def __init__(self):
        self.data = defaultdict(lambda: {
            'count': 0,
            'total_query_count': 0,
            'total_query_time': 0.0,
            'total_remaining_time': 0.0,
            'max_query_time': 0.0,
            'min_query_time': float('inf'),
            'requests': []
        })
    
    def parse_log_file(self, filepath=None, file_handle=None):
        """Parser un fichier de log ou stdin"""
        if file_handle:
            print(f"📖 Analyse depuis stdin...", file=sys.stderr)
            return self._parse_file_handle(file_handle)
        else:
            print(f"📖 Analyse du fichier: {filepath}", file=sys.stderr)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    return self._parse_file_handle(f)
            except FileNotFoundError:
                print(f"❌ Fichier non trouvé: {filepath}", file=sys.stderr)
                return False
            except Exception as e:
                print(f"❌ Erreur lors de la lecture: {e}", file=sys.stderr)
                return False
    
    def _parse_file_handle(self, f):
        """Parser depuis un file handle (fichier ou stdin)"""
        try:
            for line in f:
                self._parse_line(line)
            return True
        except Exception as e:
            print(f"❌ Erreur: {e}", file=sys.stderr)
            return False
    
    def _parse_line(self, line):
        """Parser une ligne de log"""
        # Ne traiter que les lignes werkzeug avec web_search_read
        if 'werkzeug:' not in line or 'web_search_read' not in line:
            return
        
        match = self.LOG_PATTERN.search(line)
        if not match:
            return
        
        timestamp, database, ip, method, url, status_code, content_len, query_count, query_time, remaining_time = match.groups()
        
        # Extraire le modèle de l'URL
        # Format: /web/dataset/call_kw/is.presse.cycle/web_search_read
        model_match = re.search(r'/call_kw/([^/]+)/', url)
        model = model_match.group(1) if model_match else 'unknown'
        
        # Créer la clé de synthèse: IP|Base|Modèle
        key = f"{ip} | {database} | {model}"
        
        try:
            query_count_int = int(query_count)
            query_time_float = float(query_time)
            remaining_time_float = float(remaining_time)
            
            stats = self.data[key]
            stats['count'] += 1
            stats['total_query_count'] += query_count_int
            stats['total_query_time'] += query_time_float
            stats['total_remaining_time'] += remaining_time_float
            stats['max_query_time'] = max(stats['max_query_time'], query_time_float)
            stats['min_query_time'] = min(stats['min_query_time'], query_time_float)
            
            # Garder les détails des requêtes pour les requêtes longues
            if query_time_float > 1.0:  # Marquer les requêtes > 1s
                stats['requests'].append({
                    'timestamp': timestamp,
                    'database': database,
                    'method': method,
                    'url': url,
                    'status': status_code,
                    'query_count': query_count_int,
                    'query_time': query_time_float,
                    'remaining_time': remaining_time_float
                })
        
        except (ValueError, TypeError) as e:
            pass  # Ignorer les lignes mal formatées
    
    def print_summary(self, output_file=None):
        """Afficher un résumé des performances"""
        if not self.data:
            print("⚠️ Aucune donnée trouvée", file=sys.stderr)
            return
        
        output_text = self._generate_summary_by_ip_model()
        output_text += "\n\n" + self._generate_summary_by_database()
        output_text += "\n\n" + self._generate_summary_by_site()
        output_text += "\n\n" + self._generate_summary_by_ip()
        output_text += "\n\n" + self._generate_summary_by_model()
        
        print(output_text)
        
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                print(f"\n✅ Rapport sauvegardé: {output_file}", file=sys.stderr)
            except Exception as e:
                print(f"⚠️ Impossible de sauvegarder le rapport: {e}", file=sys.stderr)
    
    def _categorize_items(self, items, key_func):
        """Séparer items en 3 catégories selon key_func retournant total_query_time"""
        rouges = [item for item in items if key_func(item) > 5.0]
        oranges = [item for item in items if 2.0 < key_func(item) <= 5.0]
        verts = [item for item in items if key_func(item) <= 2.0]
        return rouges, oranges, verts
    
    def _format_table_lines(self, items, formatter, max_items=None):
        """Formater items pour affichage en table avec séparation 3 catégories"""
        lines = []
        rouges, oranges, verts = self._categorize_items(items, formatter['key_func'])
        
        for item in rouges:
            lines.append(formatter['format']("🔴", item))
        for item in oranges:
            lines.append(formatter['format']("🟠", item))
        for item in verts[:5] if max_items else verts:
            lines.append(formatter['format']("🟢", item))
        
        if max_items and len(verts) > 5:
            lines.append(f"   ... et {len(verts) - 5} autres rapides (🟢)")
        
        return lines
    
    def _generate_summary_by_ip_model(self):
        """Générer résumé par IP et modèle"""
        sorted_data = sorted(self.data.items(), key=lambda x: x[1]['total_query_time'], reverse=True)
        
        # Préparer les données
        items = []
        totals = {'requests': 0, 'sql_time': 0.0, 'remaining_time': 0.0}
        
        for key, stats in sorted_data:
            count = stats['count']
            avg_query_time = stats['total_query_time'] / count if count > 0 else 0
            item = (key, count, avg_query_time, stats['max_query_time'], stats['total_query_time'], stats['total_remaining_time'])
            items.append(item)
            totals['requests'] += count
            totals['sql_time'] += stats['total_query_time']
            totals['remaining_time'] += stats['total_remaining_time']
        
        # Formater
        output_lines = ["\n" + "="*140, "📊 SYNTHÈSE DES PERFORMANCES web_search_read (par IP | Base | Modèle)", "="*140 + "\n"]
        output_lines.append(f"   {'IP | Base | Modèle':<51} {'Requêtes':>11} {'SQL (avg)':>13} {'SQL (max)':>13} {'Total SQL':>13} {'Hors SQL':>13}")
        output_lines.append("-" * 140)
        
        formatter = {
            'key_func': lambda x: x[4],  # total_query_time
            'format': lambda marker, item: f"{marker} {item[0]:<51} {item[1]:>11} {item[2]:>13.3f}s {item[3]:>13.3f}s {item[4]:>13.3f}s {item[5]:>13.3f}s"
        }
        output_lines.extend(self._format_table_lines(items, formatter, max_items=True))
        
        output_lines.append("-" * 140)
        output_lines.append(f"   {'TOTAL':<51} {totals['requests']:>11} {'':>13} {'':>13} {totals['sql_time']:>13.3f}s {totals['remaining_time']:>13.3f}s")
        output_lines.append("=" * 140)
        
        # Statistiques complémentaires
        output_lines.append("\n📈 STATISTIQUES COMPLÉMENTAIRES\n")
        output_lines.append(f"  • Nombre total de requêtes: {totals['requests']}")
        output_lines.append(f"  • Temps SQL total: {totals['sql_time']:.3f}s")
        output_lines.append(f"  • Temps hors SQL total: {totals['remaining_time']:.3f}s")
        if totals['requests'] > 0:
            avg_time = (totals['sql_time'] + totals['remaining_time']) / totals['requests']
            pct_sql = 100 * totals['sql_time'] / (totals['sql_time'] + totals['remaining_time'])
            output_lines.append(f"  • Temps moyen par requête: {avg_time:.3f}s")
            output_lines.append(f"  • Pourcentage SQL: {pct_sql:.1f}%")
        
        # Requêtes problématiques
        all_slow_requests = [(k, r) for k, s in sorted_data for r in s['requests']]
        if all_slow_requests:
            output_lines.append("\n" + "="*140)
            output_lines.append("🐌 REQUÊTES LENTES\n")
            output_lines.append(f"   {'Timestamp':<18} {'Base':<15} {'IP | Modèle':<48} {'Requêtes SQL':>15} {'Temps SQL':>13}")
            output_lines.append("-" * 140)
            
            sorted_requests = sorted(all_slow_requests, key=lambda x: x[1]['query_time'], reverse=True)
            formatter_req = {
                'key_func': lambda x: x[1]['query_time'],
                'format': lambda marker, item: f"{marker} {item[1]['timestamp']:<18} {item[1]['database']:<15} {item[0]:<48} {item[1]['query_count']:>15} {item[1]['query_time']:>13.3f}s"
            }
            output_lines.extend(self._format_table_lines(sorted_requests, formatter_req, max_items=True))
            output_lines.append("=" * 140)
        
        return "\n".join(output_lines)
    
    def _generate_summary_by_database(self):
        """Générer résumé par Base de Données (agrégé tous modèles/IPs)"""
        # Agréger par base
        db_stats = defaultdict(lambda: {'count': 0, 'total_query_time': 0.0, 'total_remaining_time': 0.0, 'max_query_time': 0.0})
        
        for key, stats in self.data.items():
            # key format: "IP | Base | Modèle"
            parts = key.split(' | ')
            if len(parts) >= 2:
                database = parts[1]
                db_stats[database]['count'] += stats['count']
                db_stats[database]['total_query_time'] += stats['total_query_time']
                db_stats[database]['total_remaining_time'] += stats['total_remaining_time']
                db_stats[database]['max_query_time'] = max(db_stats[database]['max_query_time'], stats['max_query_time'])
        
        sorted_by_db = sorted(db_stats.items(), key=lambda x: x[1]['total_query_time'], reverse=True)
        
        # Préparer items
        items = [(k, v['count'], v['total_query_time']/v['count'] if v['count'] > 0 else 0, v['max_query_time'], v['total_query_time'], v['total_remaining_time']) 
                 for k, v in sorted_by_db]
        
        output_lines = ["\n" + "="*100, "🗄️ SYNTHÈSE DES PERFORMANCES par BASE DE DONNÉES", "="*100 + "\n"]
        output_lines.append(f"   {'Base de Données':<21} {'Requêtes':>11} {'SQL (avg)':>13} {'SQL (max)':>13} {'Total SQL':>13} {'Hors SQL':>13}")
        output_lines.append("-" * 100)
        
        formatter = {
            'key_func': lambda x: x[4],
            'format': lambda marker, item: f"{marker} {item[0]:<21} {item[1]:>11} {item[2]:>13.3f}s {item[3]:>13.3f}s {item[4]:>13.3f}s {item[5]:>13.3f}s"
        }
        output_lines.extend(self._format_table_lines(items, formatter, max_items=True))
        output_lines.append("=" * 100)
        
        return "\n".join(output_lines)
    
    def _generate_summary_by_site(self):
        """Générer résumé par Site (2 premiers octets de l'IP)"""
        # Agréger par site (2 premiers octets de l'IP)
        site_stats = defaultdict(lambda: {'count': 0, 'total_query_time': 0.0, 'total_remaining_time': 0.0, 'max_query_time': 0.0})
        
        for key, stats in self.data.items():
            # key format: "IP | Base | Modèle"
            ip = key.split(' | ')[0]
            # Extraire les 2 premiers octets de l'IP
            site = '.'.join(ip.split('.')[:2])
            site_stats[site]['count'] += stats['count']
            site_stats[site]['total_query_time'] += stats['total_query_time']
            site_stats[site]['total_remaining_time'] += stats['total_remaining_time']
            site_stats[site]['max_query_time'] = max(site_stats[site]['max_query_time'], stats['max_query_time'])
        
        sorted_by_site = sorted(site_stats.items(), key=lambda x: x[1]['total_query_time'], reverse=True)
        
        # Préparer items
        items = [(k, v['count'], v['total_query_time']/v['count'] if v['count'] > 0 else 0, v['max_query_time'], v['total_query_time'], v['total_remaining_time']) 
                 for k, v in sorted_by_site]
        
        output_lines = ["\n" + "="*100, "🌐 SYNTHÈSE DES PERFORMANCES par SITE (2 premiers octets IP)", "="*100 + "\n"]
        output_lines.append(f"   {'Site':<16} {'Requêtes':>11} {'SQL (avg)':>13} {'SQL (max)':>13} {'Total SQL':>13} {'Hors SQL':>13}")
        output_lines.append("-" * 100)
        
        formatter = {
            'key_func': lambda x: x[4],
            'format': lambda marker, item: f"{marker} {item[0]:<16} {item[1]:>11} {item[2]:>13.3f}s {item[3]:>13.3f}s {item[4]:>13.3f}s {item[5]:>13.3f}s"
        }
        output_lines.extend(self._format_table_lines(items, formatter, max_items=True))
        output_lines.append("=" * 100)
        
        return "\n".join(output_lines)
    
    def _generate_summary_by_ip(self):
        """Générer résumé par IP (agrégé tous modèles)"""
        # Agréger par IP
        ip_stats = defaultdict(lambda: {'count': 0, 'total_query_time': 0.0, 'total_remaining_time': 0.0, 'max_query_time': 0.0})
        
        for key, stats in self.data.items():
            ip = key.split(' | ')[0]
            ip_stats[ip]['count'] += stats['count']
            ip_stats[ip]['total_query_time'] += stats['total_query_time']
            ip_stats[ip]['total_remaining_time'] += stats['total_remaining_time']
            ip_stats[ip]['max_query_time'] = max(ip_stats[ip]['max_query_time'], stats['max_query_time'])
        
        sorted_by_ip = sorted(ip_stats.items(), key=lambda x: x[1]['total_query_time'], reverse=True)
        
        # Préparer items
        items = [(k, v['count'], v['total_query_time']/v['count'] if v['count'] > 0 else 0, v['max_query_time'], v['total_query_time'], v['total_remaining_time']) 
                 for k, v in sorted_by_ip]
        
        output_lines = ["\n" + "="*100, "📡 SYNTHÈSE DES PERFORMANCES par ADRESSE IP", "="*100 + "\n"]
        output_lines.append(f"   {'IP':<16} {'Requêtes':>11} {'SQL (avg)':>13} {'SQL (max)':>13} {'Total SQL':>13} {'Hors SQL':>13}")
        output_lines.append("-" * 100)
        
        formatter = {
            'key_func': lambda x: x[4],
            'format': lambda marker, item: f"{marker} {item[0]:<16} {item[1]:>11} {item[2]:>13.3f}s {item[3]:>13.3f}s {item[4]:>13.3f}s {item[5]:>13.3f}s"
        }
        output_lines.extend(self._format_table_lines(items, formatter, max_items=True))
        output_lines.append("=" * 100)
        
        return "\n".join(output_lines)
    
    def _generate_summary_by_model(self):
        """Générer résumé par Modèle (agrégé toutes IPs et bases)"""
        # Agréger par modèle
        model_stats = defaultdict(lambda: {'count': 0, 'total_query_time': 0.0, 'total_remaining_time': 0.0, 'max_query_time': 0.0})
        
        for key, stats in self.data.items():
            # key format: "IP | Base | Modèle"
            parts = key.split(' | ')
            if len(parts) >= 3:
                model = parts[2]
                model_stats[model]['count'] += stats['count']
                model_stats[model]['total_query_time'] += stats['total_query_time']
                model_stats[model]['total_remaining_time'] += stats['total_remaining_time']
                model_stats[model]['max_query_time'] = max(model_stats[model]['max_query_time'], stats['max_query_time'])
        
        sorted_by_model = sorted(model_stats.items(), key=lambda x: x[1]['total_query_time'], reverse=True)
        
        # Préparer items
        items = [(k, v['count'], v['total_query_time']/v['count'] if v['count'] > 0 else 0, v['max_query_time'], v['total_query_time'], v['total_remaining_time']) 
                 for k, v in sorted_by_model]
        
        output_lines = ["\n" + "="*100, "🗂️ SYNTHÈSE DES PERFORMANCES par MODÈLE", "="*100 + "\n"]
        output_lines.append(f"   {'Modèle':<31} {'Requêtes':>11} {'SQL (avg)':>13} {'SQL (max)':>13} {'Total SQL':>13} {'Hors SQL':>13}")
        output_lines.append("-" * 100)
        
        formatter = {
            'key_func': lambda x: x[4],
            'format': lambda marker, item: f"{marker} {item[0]:<31} {item[1]:>11} {item[2]:>13.3f}s {item[3]:>13.3f}s {item[4]:>13.3f}s {item[5]:>13.3f}s"
        }
        output_lines.extend(self._format_table_lines(items, formatter, max_items=True))
        output_lines.append("=" * 100)
        
        return "\n".join(output_lines)


def main():
    if len(sys.argv) < 2:
        # Lire depuis stdin
        analyzer = LogAnalyzer()
        if not sys.stdin.isatty():
            if analyzer.parse_log_file(file_handle=sys.stdin):
                analyzer.print_summary()
            else:
                sys.exit(1)
        else:
            print("Usage: analyse-log.py [fichier_log] [fichier_sortie]", file=sys.stderr)
            print("       cat odoo.log | analyse-log.py [fichier_sortie]", file=sys.stderr)
            print("\nExemples:", file=sys.stderr)
            print("  python3 analyse-log.py /var/log/odoo/odoo.log", file=sys.stderr)
            print("  python3 analyse-log.py /var/log/odoo/odoo.log rapport.txt", file=sys.stderr)
            print("  cat /var/log/odoo/odoo.log | python3 analyse-log.py", file=sys.stderr)
            print("  cat /var/log/odoo/odoo.log | python3 analyse-log.py rapport.txt", file=sys.stderr)
            sys.exit(1)
    else:
        log_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        
        analyzer = LogAnalyzer()
        
        if analyzer.parse_log_file(filepath=log_file):
            analyzer.print_summary(output_file)
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()
