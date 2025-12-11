# DupliCheck

**Détection et gestion interactive des doublons pour QGIS**

![QGIS](https://img.shields.io/badge/QGIS-3.22+-green.svg)
![License](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Version](https://img.shields.io/badge/Version-1.0.0-orange.svg)

## Présentation

DupliCheck est un plugin QGIS permettant de détecter et de gérer les entités en doublon dans les couches vectorielles. Contrairement aux outils natifs de QGIS qui suppriment automatiquement les doublons, DupliCheck présente les résultats de manière interactive et vous permet de décider quelles entités conserver ou supprimer.

## Fonctionnalités

- **Détection de doublons géométriques** - Exacte ou avec tolérance configurable  
- **Détection de doublons attributaires** - Comparaison sur un ou plusieurs champs  
- **Gestion par groupes** - Prend en charge N doublons, pas seulement des paires  
- **Visualisation interactive** - Mise en évidence sur la carte QGIS principale  
- **Cliquez pour zoomer** - Un clic pour surligner, double-clic pour zoomer  
- **Règles de priorité configurables** - Date, complétude, superficie, FID  
- **Score de confiance** - Pour chaque groupe de doublons  
- **Export de rapports** - Formats CSV, Excel, GeoPackage  
- **Snapshot/restauration** - Opérations sûres avec possibilité d'annulation  
- **Multilingue** - 9 langues disponibles : français, anglais, espagnol, arabe, allemand, russe, chinois, portugais, italien

## Installation

### Depuis le fichier ZIP

1. Téléchargez la dernière version en ZIP  
2. Dans QGIS : `Plugins` → `Gérer et installer des plugins` → `Installer depuis un ZIP`  
3. Sélectionnez le fichier ZIP téléchargé  
4. Redémarrez QGIS si nécessaire  

### Installation manuelle

1. Décompressez le ZIP dans le dossier des plugins QGIS :  
   - Windows : `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`  
   - Linux : `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`  
   - macOS : `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`  
2. Redémarrez QGIS  
3. Activez le plugin dans `Plugins` → `Gérer et installer des plugins`

## Utilisation

### Workflow de base

1. **Ouvrir DupliCheck** depuis le menu Vectoriel ou la barre d’outils  
2. **Sélectionner une couche** à analyser  
3. **Choisir le type de détection** :  
   - Géométrique : identifie les entités aux géométries identiques ou similaires  
   - Attributaire : identifie les entités aux valeurs d’attributs correspondantes  
4. **Configurer les options** (tolérance, champs à comparer, etc.)  
5. **Lancer la détection**  
6. **Consulter les résultats** dans l’onglet Résultats  
7. **Cliquer sur les entités** pour les mettre en surbrillance et zoomer sur la carte  
8. **Marquer les actions** (Keep/Remove) pour chaque entité  
9. **Appliquer les actions** pour supprimer les entités marquées

### Interactions

| Action | Résultat |
|--------|----------|
| Clic sur une entité | Surligner + zoom |
| Double-clic sur une entité | Zoom rapproché |
| Clic sur un groupe | Surligner toutes les entités du groupe |
| Double-clic sur un groupe | Zoom sur tout le groupe |

## Prérequis

- QGIS 3.22 ou supérieur  
- Python 3.9 ou supérieur

## 🧾 Journal des versions

| Version | Date       | Changements majeurs                                                                                   |
| ------- | ---------- | ---------------------------------------------------------------------------------------------------- |
| 1.0.0   | 2025-12-08 | Version initiale        |


## Licence

Licence publique générale GNU v3.0

## 💬 Retours et contributions

Vous pouvez :
- 🐛 Signaler un bug via [GitHub Issues](https://github.com/AzizT-dev/duplicheck/issues)
- 💡 Proposer des améliorations
- 🌍 Contribuer aux traductions (FR | EN | ES | AR | DE | RU | ZH | PT | IT)
- 📖 Améliorer la documentation
- ⭐ Partager vos retours d'expérience
- 🔧 Soumettre des Pull Requests

**Processus de contribution** :
1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

## 📚 Documentation complète

- 📘 [Guide utilisateur](docs/user_guide.md)
- 🎓 [Guide de configuration](docs/config_guide.md)
- 🔧 [Guide développeur](docs/developer_guide.md)
- 🐛 [FAQ & Troubleshooting](docs/faq.md)

---

## 🙏 Remerciements

Merci à la communauté QGIS pour l'API robuste et la documentation excellente.  
Merci aux testeurs beta pour leurs retours précieux.  
Merci aux utilisateurs pour leurs suggestions d'amélioration.

---

## 📊 Statistiques du projet

![GitHub stars](https://img.shields.io/github/stars/AzizT-dev/duplicheck?style=social)
![GitHub forks](https://img.shields.io/github/forks/AzizT-dev/duplicheck?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/AzizT-dev/duplicheck?style=social)

---

**⭐ Si ce plugin vous est utile, n'oubliez pas de mettre une étoile sur GitHub !**

---

<div align="center">
  
### Développé par Aziz TRAORE

**v1.0.0 - Décembre 2025**

</div>
