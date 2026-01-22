# Guide de Déploiement Vercel

## Étape 1 : Créer une base de données MongoDB Atlas (GRATUIT)

1. Allez sur https://www.mongodb.com/cloud/atlas/register
2. Créez un compte gratuit
3. Créez un nouveau cluster (tier gratuit M0)
4. Dans "Database Access", créez un utilisateur avec un mot de passe
5. Dans "Network Access", ajoutez `0.0.0.0/0` pour autoriser toutes les connexions
6. Cliquez sur "Connect" > "Connect your application"
7. Copiez l'URL de connexion qui ressemble à :
   ```
   mongodb+srv://username:password@cluster.xxxxx.mongodb.net/
   ```

## Étape 2 : Configurer les Variables d'Environnement sur Vercel

1. Allez dans votre projet sur Vercel : https://vercel.com/dashboard
2. Cliquez sur votre projet "numero"
3. Allez dans "Settings" > "Environment Variables"
4. Ajoutez les variables suivantes :

### Variables OBLIGATOIRES :

| Nom | Valeur | Description |
|-----|--------|-------------|
| `MONGODB_URL` | `mongodb+srv://...` | URL de connexion MongoDB Atlas copiée à l'étape 1 |
| `MONGODB_DB_NAME` | `qrgen` | Nom de la base de données |
| `SECRET_KEY` | `9c67c059a314afd446ecd476c6f6f23d3b115a88353bdd7ee3c1b9038c3fdb66` | Clé secrète JWT |
| `ADMIN_PASSWORD` | `votre_mot_de_passe_admin` | Mot de passe admin |

### Variables OPTIONNELLES :

| Nom | Valeur par défaut | Description |
|-----|-------------------|-------------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Durée de vie du token d'accès |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | `1440` | Durée de vie du token de rafraîchissement |
| `EMAIL_FROM` | `no-reply@example.com` | Email d'envoi |

5. Cliquez sur "Add" pour chaque variable
6. Sélectionnez "Production", "Preview" et "Development" pour chaque variable

## Étape 3 : Redéployer

1. Allez dans l'onglet "Deployments"
2. Cliquez sur "Redeploy" sur le dernier déploiement
3. Attendez que le déploiement se termine

## Étape 4 : Vérifier

1. Visitez votre URL Vercel (ex: `https://numero.vercel.app`)
2. Testez la page d'accueil
3. Testez la connexion admin à `/admin/login`

## Problèmes courants

### Erreur 500 : Internal Server Error
- Vérifiez que toutes les variables d'environnement sont configurées
- Vérifiez que MongoDB Atlas autorise les connexions depuis n'importe quelle IP (`0.0.0.0/0`)
- Vérifiez les logs Vercel : Projet > Deployments > Cliquez sur le déploiement > Runtime Logs

### Erreur de connexion MongoDB
- Vérifiez que l'URL MongoDB est correcte
- Vérifiez que le mot de passe ne contient pas de caractères spéciaux (sinon encodez-les en URL)
- Vérifiez que votre cluster MongoDB Atlas est actif

### Fichiers statiques ne se chargent pas
- Les fichiers statiques sont dans `backend/static/`
- Vérifiez que le dossier existe et contient `style.css`

## Structure du projet pour Vercel

```
/
├── api/
│   └── index.py          # Point d'entrée Vercel (importe backend/app/main.py)
├── backend/
│   ├── app/
│   │   ├── main.py       # Application FastAPI
│   │   ├── db.py         # Configuration MongoDB
│   │   └── ...
│   ├── static/           # Fichiers CSS/JS
│   └── templates/        # Templates HTML
├── vercel.json           # Configuration Vercel
├── requirements.txt      # Dépendances Python
└── runtime.txt           # Version Python (python-3.11)
```

## Support

Si le problème persiste, vérifiez les logs dans Vercel :
1. Projet > Deployments
2. Cliquez sur le déploiement
3. Onglet "Runtime Logs" pour voir les erreurs Python
