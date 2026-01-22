# Correctifs pour Vercel - Erreur 500

## Problèmes Corrigés

### 1. ✅ StaticFiles incompatible avec Vercel serverless
- **Avant** : Utilisation de `app.mount("/static", StaticFiles(...))`
- **Après** : Route FastAPI `/static/{file_path}` pour servir les fichiers
- **Fichier** : `backend/app/main.py:58-66`

### 2. ✅ Ajout de logs de débogage
- Logs lors de l'initialisation MongoDB
- Vérification de l'existence du dossier templates
- **Fichier** : `backend/app/main.py:17-20, 27-29`

### 3. ✅ Route de health check
- Nouvelle route `/health` pour diagnostiquer les problèmes
- Affiche la configuration Python, chemins, et variables d'environnement
- **Fichier** : `backend/app/main.py:42-54`

### 4. ✅ Configuration MongoDB locale
- Ajout de `MONGODB_URL` et `MONGODB_DB_NAME` dans `backend/.env`

### 5. ✅ Format runtime.txt
- Correction de `python3.11` → `python-3.11`

### 6. ✅ Fichier .vercelignore
- Optimisation du déploiement en excluant les fichiers inutiles

## Étapes de Déploiement

### Option 1 : Via Git (RECOMMANDÉ)

```bash
# 1. Commit les changements
git add .
git commit -m "Fix: Vercel serverless compatibility"

# 2. Push vers GitHub/GitLab
git push origin main

# Vercel déploiera automatiquement
```

### Option 2 : Via Vercel CLI

```bash
# Dans le dossier du projet
vercel --prod
```

## Configuration des Variables d'Environnement sur Vercel

**CRITIQUE** : Vous DEVEZ configurer ces variables dans Vercel Dashboard

1. Allez sur : https://vercel.com/dashboard
2. Sélectionnez votre projet
3. **Settings** → **Environment Variables**
4. Ajoutez ces variables pour **Production, Preview, et Development** :

### Variables OBLIGATOIRES

| Variable | Valeur | Où la trouver |
|----------|--------|---------------|
| `MONGODB_URL` | `mongodb+srv://user:pass@cluster.mongodb.net/` | Après création cluster MongoDB Atlas |
| `MONGODB_DB_NAME` | `qrgen` | Nom de votre choix |
| `SECRET_KEY` | `9c67c059a314afd446ecd476c6f6f23d3b115a88353bdd7ee3c1b9038c3fdb66` | Déjà dans .env |
| `ADMIN_PASSWORD` | `votre_mot_de_passe_sécurisé` | Choisissez un mot de passe fort |

### Variables OPTIONNELLES

| Variable | Valeur par défaut |
|----------|-------------------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | `1440` |

## Créer MongoDB Atlas (si pas encore fait)

1. **Créer un compte** : https://www.mongodb.com/cloud/atlas/register
2. **Créer un cluster** : Choisir le plan **Free (M0)**
3. **Database Access** :
   - Créer un utilisateur (username + password)
   - Noter le mot de passe !
4. **Network Access** :
   - Add IP Address → `0.0.0.0/0` (autoriser toutes les IP)
5. **Connect** :
   - Connect your application
   - Copier l'URL : `mongodb+srv://username:<password>@cluster.xxxxx.mongodb.net/`
   - **IMPORTANT** : Remplacer `<password>` par votre vrai mot de passe

## Vérification Post-Déploiement

### 1. Tester le Health Check

```bash
curl https://dynamique-qrcode.vercel.app/health
```

**Réponse attendue** :
```json
{
  "status": "ok",
  "python_version": "3.11.x",
  "templates_dir": "/var/task/backend/templates",
  "templates_exists": true,
  "pwd": "/var/task",
  "env_vars": {
    "MONGODB_URL": "configured",
    "MONGODB_DB_NAME": "qrgen"
  }
}
```

### 2. Tester la Page d'Accueil

```bash
curl https://dynamique-qrcode.vercel.app/
```

Devrait retourner le HTML de `index.html`

### 3. Vérifier les Logs

1. Vercel Dashboard → Votre projet
2. **Deployments** → Cliquer sur le dernier déploiement
3. **Runtime Logs** → Chercher les erreurs

## Problèmes Fréquents

### Erreur : "MONGODB_URL: missing"

**Cause** : Variable d'environnement non configurée sur Vercel

**Solution** :
1. Vercel Dashboard → Settings → Environment Variables
2. Ajouter `MONGODB_URL` avec votre URL MongoDB Atlas
3. Redéployer

### Erreur : "Templates directory does not exist"

**Cause** : Le dossier `backend/templates/` n'est pas déployé

**Solution** :
```bash
# Vérifier localement
ls -la backend/templates/

# Si vide, il manque les fichiers HTML
```

### Erreur 500 persistante

**Diagnostic** :
```bash
# Voir les logs détaillés
vercel logs https://dynamique-qrcode.vercel.app --json

# Ou via le dashboard Vercel
```

**Solutions courantes** :
1. Vérifier toutes les variables d'environnement
2. Vérifier que MongoDB Atlas autorise les connexions
3. Vérifier que le dossier `backend/templates/` contient les fichiers HTML

## Commandes Utiles

```bash
# Lister les déploiements
vercel ls

# Voir les logs du dernier déploiement
vercel logs <deployment-url>

# Redéployer en production
vercel --prod

# Tester en local avec env Vercel
vercel dev
```

## Checklist Finale

- [ ] Variables d'environnement configurées sur Vercel
- [ ] MongoDB Atlas créé et accessible
- [ ] Code poussé sur Git
- [ ] Déploiement Vercel réussi
- [ ] `/health` retourne `"status": "ok"`
- [ ] Page d'accueil `/` accessible
- [ ] Admin `/admin/login` accessible

## Support

Si le problème persiste après ces étapes :
1. Vérifiez les **Runtime Logs** dans Vercel Dashboard
2. Testez `/health` pour voir la configuration
3. Vérifiez que MongoDB Atlas autorise les connexions depuis `0.0.0.0/0`
