"""
Module de gestion des coûts de transaction
"""

import backtrader as bt


class SimpleCosts(bt.CommInfoBase):
    """
    Classe de commission simple - taux proportionnel par exécution
    """
    
    params = (
        ('commission', 0.0002),  # 0.02% par défaut
        ('commtype', bt.CommInfoBase.COMM_PERC),  # commission en pourcentage
        ('stocklike', True),  # pour actions/CFD
    )
    
    def _getcommission(self, size, price, pseudoexec):
        """
        Calcule la commission pour une exécution
        
        Args:
            size: taille de la position
            price: prix d'exécution
            pseudoexec: flag Backtrader
            
        Returns:
            commission en valeur absolue
        """
        return abs(size) * price * self.p.commission
