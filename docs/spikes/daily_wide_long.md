Le but du spike wide/long est de déterminer une représentation adaptée aux observations quotidiennes meteo.data.gouv.fr en comparant un stockage source-shaped wide à un modèle générique long, en termes de densité, volume, facilité d'ingestion et performances de quelques requêtes analytiques.

### Résultats provisoires du spike

#### Densité des données
- Densité RR-T-Vent core : 45,0 %
- Densité RR-T-Vent tous : 13,9 %
- Densité autres-parametres tous : 9,27 %

#### Taille des DataFrame en Polars

Avant normalisation du long (station_id, source_file, obs_date, param_code, value, quality_code, status_code) 

```python
df_rtv_all.estimated_size("mb")
276.61173915863037
df_long_rtv_all.estimated_size("mb")
248.50394916534424
df_autres_all.estimated_size("mb")
182.91388130187988
```
