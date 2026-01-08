#!/usr/bin/env python3
"""
Trading Windows Filter
Permet de définir des créneaux horaires spécifiques pour le trading
Format: "Monday[13:00-16:00]"
"""

import re
from datetime import time
import pytz


class TradingWindows:
    """
    Gère les créneaux horaires de trading autorisés
    
    Format des windows: "Day[HH:MM-HH:MM]"
    Exemple: "Monday[13:00-16:00]"
    """
    
    VALID_DAYS = [
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 
        'Friday', 'Saturday', 'Sunday'
    ]
    
    # Pattern regex pour parser "Monday[13:00-16:00]"
    WINDOW_PATTERN = re.compile(
        r'^(\w+)\[(\d{2}):(\d{2})-(\d{2}):(\d{2})\]$'
    )
    
    def __init__(self, config=None):
        """
        Initialise les filtres temporels
        
        Args:
            config: Dict avec:
                - enabled: bool
                - timezone: str (ex: "Europe/Paris")
                - windows: list[str] (ex: ["Monday[13:00-16:00]"]) OU "always"
        """
        if config is None:
            config = {}
        
        self.enabled = config.get('enabled', False)
        self.timezone_str = config.get('timezone', 'Europe/Paris')
        self.timezone = pytz.timezone(self.timezone_str)
        self.windows = []
        self.always_mode = False
        
        # Check si mode "always" (trade 24/7)
        raw_windows = config.get('windows', [])
        
        if raw_windows == "always":
            # Mode 24/7 - créer windows pour toute la semaine
            self.always_mode = True
            for day in self.VALID_DAYS:
                self.windows.append({
                    'day': day,
                    'start_time': time(0, 0),
                    'end_time': time(23, 59),
                    'original': f"{day}[00:00-23:59]"
                })
            print("⏰ Trading Windows: 24/7 mode enabled")
            return
        
        # Parser les windows normalement
        for window_str in raw_windows:
            parsed = self._parse_window(window_str)
            if parsed:
                self.windows.append(parsed)
            else:
                print(f"⚠️  Invalid window format: {window_str}")
        
        if self.enabled and len(self.windows) == 0:
            print("⚠️  Trading windows enabled but no valid windows defined!")
        
        # Stats
        self._log_summary()
    
    def _parse_window(self, window_str):
        """
        Parse une string "Monday[13:00-16:00]" en dict
        
        Returns:
            dict avec day, start_time, end_time ou None si invalide
        """
        match = self.WINDOW_PATTERN.match(window_str.strip())
        if not match:
            return None
        
        day, start_h, start_m, end_h, end_m = match.groups()
        
        # Valider le jour (case-insensitive)
        day_capitalized = day.capitalize()  # wednesday -> Wednesday
        if day_capitalized not in self.VALID_DAYS:
            print(f"⚠️  Invalid day: {day}")
            return None
        
        # Utiliser le nom capitalisé pour la suite
        day = day_capitalized
        
        # Convertir en int
        try:
            start_h = int(start_h)
            start_m = int(start_m)
            end_h = int(end_h)
            end_m = int(end_m)
        except ValueError:
            return None
        
        # Valider les heures/minutes
        if not (0 <= start_h <= 23 and 0 <= start_m <= 59):
            print(f"⚠️  Invalid start time: {start_h}:{start_m}")
            return None
        
        if not (0 <= end_h <= 23 and 0 <= end_m <= 59):
            print(f"⚠️  Invalid end time: {end_h}:{end_m}")
            return None
        
        start_time = time(start_h, start_m)
        end_time = time(end_h, end_m)
        
        # Vérifier que end > start
        if end_time <= start_time:
            print(f"⚠️  End time must be after start time: {window_str}")
            return None
        
        return {
            'day': day,
            'start_time': start_time,
            'end_time': end_time,
            'original': window_str
        }
    
    def is_trading_allowed(self, current_datetime):
        """
        Vérifie si le trading est autorisé à cet instant
        
        Args:
            current_datetime: datetime (peut être tz-aware ou naive)
        
        Returns:
            bool: True si trading autorisé
        """
        if not self.enabled:
            return True  # Filtre désactivé → toujours autorisé
        
        # Convertir en timezone configuré
        if current_datetime.tzinfo is None:
            # Naive → localiser dans le timezone configuré
            dt = self.timezone.localize(current_datetime)
        else:
            # Aware → convertir dans le timezone configuré
            dt = current_datetime.astimezone(self.timezone)
        
        current_day = dt.strftime('%A')  # Monday, Tuesday, etc.
        current_time = dt.time()
        
        # Vérifier si dans un des créneaux autorisés
        for window in self.windows:
            if window['day'] == current_day:
                if window['start_time'] <= current_time <= window['end_time']:
                    return True  # Dans un créneau autorisé
        
        return False  # Aucun créneau ne correspond
    
    def get_active_windows_for_day(self, day_name):
        """Retourne tous les créneaux actifs pour un jour donné"""
        return [w for w in self.windows if w['day'] == day_name]
    
    def get_total_hours_per_week(self):
        """Calcule le nombre total d'heures de trading par semaine"""
        total_minutes = 0
        for window in self.windows:
            start_minutes = window['start_time'].hour * 60 + window['start_time'].minute
            end_minutes = window['end_time'].hour * 60 + window['end_time'].minute
            total_minutes += (end_minutes - start_minutes)
        return total_minutes / 60.0
    
    def _log_summary(self):
        """Affiche un résumé des créneaux configurés"""
        if not self.enabled:
            return
        
        print("\n" + "="*70)
        print("⏰ TRADING WINDOWS CONFIGURATION")
        print("="*70)
        
        if self.always_mode:
            print("Mode: 24/7 (Always trading)")
            print("Timezone: (not applicable)")
            print("Total hours/week: 168.0h (100% of week)")
            print("="*70 + "\n")
            return
        
        print(f"Timezone: {self.timezone_str}")
        print(f"Total windows: {len(self.windows)}")
        print(f"Total hours/week: {self.get_total_hours_per_week():.1f}h "
              f"({self.get_total_hours_per_week()/168*100:.1f}% of week)")
        print("\nActive windows:")
        
        # Grouper par jour
        by_day = {}
        for window in self.windows:
            day = window['day']
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(window)
        
        # Afficher par ordre des jours
        for day in self.VALID_DAYS:
            if day in by_day:
                windows_str = ', '.join([
                    f"{w['start_time'].strftime('%H:%M')}-{w['end_time'].strftime('%H:%M')}"
                    for w in by_day[day]
                ])
                print(f"  {day:10s}: {windows_str}")
        
        print("="*70 + "\n")


if __name__ == '__main__':
    # Test
    config = {
        'enabled': True,
        'timezone': 'Europe/Paris',
        'windows': [
            'Monday[13:00-16:00]',
            'Monday[20:00-22:00]',
            'Tuesday[09:00-11:30]',
            'Friday[08:00-12:00]'
        ]
    }
    
    tw = TradingWindows(config)
    
    # Test quelques dates
    from datetime import datetime
    
    test_dates = [
        datetime(2024, 6, 17, 14, 30),  # Monday 14:30 → dans créneau
        datetime(2024, 6, 17, 12, 0),   # Monday 12:00 → hors créneau
        datetime(2024, 6, 18, 10, 0),   # Tuesday 10:00 → dans créneau
        datetime(2024, 6, 19, 10, 0),   # Wednesday 10:00 → hors créneau
    ]
    
    for dt in test_dates:
        allowed = tw.is_trading_allowed(dt)
        print(f"{dt.strftime('%A %H:%M')}: {'✅ ALLOWED' if allowed else '❌ BLOCKED'}")
