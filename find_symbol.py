#!/usr/bin/env python
"""
Script pour trouver le bon nom de symbole MT5

Recherche des symboles NAS100, NASDAQ, US100, etc.
"""

import MetaTrader5 as mt5
from datetime import datetime

print("="*80)
print("🔍 RECHERCHE DE SYMBOLES MT5")
print("="*80)
print()

# Initialiser MT5
print("Initialisation MT5...")
if not mt5.initialize():
    print("❌ Erreur: MT5 n'a pas pu s'initialiser")
    print("Assure-toi que MT5 est ouvert et connecté")
    input("\nAppuie sur Entrée pour quitter...")
    quit()

print("✅ MT5 initialisé")
print()

# Rechercher des symboles
search_terms = ['NAS', 'NDX', 'US100', 'US Tech', 'NASDAQ']

print("="*80)
print("RECHERCHE DE SYMBOLES NASDAQ/NAS100")
print("="*80)
print()

all_symbols = mt5.symbols_get()
print(f"Total de symboles disponibles: {len(all_symbols)}")
print()

found_symbols = []

for term in search_terms:
    print(f"🔍 Recherche: '{term}'...")
    
    # Recherche insensible à la casse
    matches = [s for s in all_symbols if term.upper() in s.name.upper()]
    
    if matches:
        print(f"   ✅ {len(matches)} symboles trouvés:")
        for symbol in matches[:10]:  # Limite à 10 résultats par terme
            print(f"      - {symbol.name}")
            if symbol not in found_symbols:
                found_symbols.append(symbol)
    else:
        print(f"   ❌ Aucun symbole trouvé")
    print()

# Afficher tous les symboles trouvés avec détails
if found_symbols:
    print("="*80)
    print(f"📊 SYMBOLES CANDIDATS ({len(found_symbols)} trouvés)")
    print("="*80)
    print()
    
    for i, symbol in enumerate(found_symbols, 1):
        print(f"{i}. {symbol.name}")
        print(f"   Description: {symbol.description}")
        print(f"   Path: {symbol.path}")
        print(f"   Visible: {symbol.visible}")
        print(f"   Digits: {symbol.digits}")
        
        # Tester si on peut récupérer des données
        try:
            rates = mt5.copy_rates_from_pos(symbol.name, mt5.TIMEFRAME_M1, 0, 10)
            if rates is not None and len(rates) > 0:
                print(f"   ✅ Données M1 disponibles ({len(rates)} bars)")
                last_time = datetime.fromtimestamp(rates[-1]['time'])
                print(f"   Dernière bougie: {last_time}")
            else:
                print(f"   ⚠️  Pas de données M1 disponibles")
        except Exception as e:
            print(f"   ❌ Erreur lors du test: {e}")
        
        print()

    # Recommandation
    print("="*80)
    print("💡 RECOMMANDATION")
    print("="*80)
    print()
    
    # Trouver le meilleur candidat
    best_candidate = None
    
    # Priorité 1: Symboles avec "NAS100" exact
    for s in found_symbols:
        if 'NAS100' in s.name.upper():
            best_candidate = s
            break
    
    # Priorité 2: Symboles avec "US100"
    if not best_candidate:
        for s in found_symbols:
            if 'US100' in s.name.upper():
                best_candidate = s
                break
    
    # Priorité 3: Symboles avec "NDX" ou "NASDAQ"
    if not best_candidate:
        for s in found_symbols:
            if 'NDX' in s.name.upper() or 'NASDAQ' in s.name.upper():
                best_candidate = s
                break
    
    # Priorité 4: Premier symbole visible avec données
    if not best_candidate:
        for s in found_symbols:
            if s.visible:
                rates = mt5.copy_rates_from_pos(s.name, mt5.TIMEFRAME_M1, 0, 1)
                if rates is not None and len(rates) > 0:
                    best_candidate = s
                    break
    
    if best_candidate:
        print(f"✅ Symbole recommandé: {best_candidate.name}")
        print(f"   Description: {best_candidate.description}")
        print()
        print(f"📝 Utilise ce symbole dans tes configs:")
        print(f"   symbol: \"{best_candidate.name}\"")
        print()
    else:
        print("⚠️  Aucun symbole optimal trouvé")
        print("   Utilise un des symboles listés ci-dessus")
        print()

else:
    print("="*80)
    print("⚠️  AUCUN SYMBOLE NASDAQ TROUVÉ")
    print("="*80)
    print()
    print("Essaye de chercher manuellement dans MT5:")
    print("1. Ouvre MT5")
    print("2. Menu: Affichage > Symboles (Ctrl+U)")
    print("3. Cherche 'NASDAQ', 'NAS', 'US100', etc.")
    print()

# Afficher aussi les symboles Forex populaires pour référence
print("="*80)
print("📈 AUTRES SYMBOLES POPULAIRES (FOREX)")
print("="*80)
print()

forex_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD']
for symbol_name in forex_symbols:
    symbols = [s for s in all_symbols if symbol_name in s.name.upper()]
    if symbols:
        symbol = symbols[0]
        print(f"✅ {symbol.name}")
        
        # Test données
        rates = mt5.copy_rates_from_pos(symbol.name, mt5.TIMEFRAME_M1, 0, 1)
        if rates is not None and len(rates) > 0:
            print(f"   Données M1 disponibles")
    else:
        print(f"❌ {symbol_name} non trouvé")

print()

# Shutdown MT5
mt5.shutdown()

print("="*80)
print("FIN")
print("="*80)

input("\nAppuie sur Entrée pour quitter...")
