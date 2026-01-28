// /api/webhooks/test-dropbox.js
import { Dropbox } from 'dropbox';

export default async function handler(req, res) {
  try {
    const dbx = new Dropbox({
      clientId: process.env.DROPBOX_APP_KEY,
      clientSecret: process.env.DROPBOX_APP_SECRET,
      refreshToken: process.env.DROPBOX_REFRESH_TOKEN,
    });

    const result = await dbx.filesListFolder({
      path: process.env.DROPBOX_FOLDER_PATH || '',
    });

    res.status(200).json({
      success: true,
      files: result.result.entries.map(e => e.name),
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
      error_type: error.constructor.name,
    });
  }
}
