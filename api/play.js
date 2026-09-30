import crypto from 'crypto';

const SECRET_KEY = process.env.SECRET_KEY || 'MySuperSecretKey2026_ChangeMe3222';
const KEY = Buffer.from(SECRET_KEY);

function decryptToken(token) {
  try {
    const iv_ct = Buffer.from(token, 'base64');
    const iv = iv_ct.slice(0, 16);
    const ct = iv_ct.slice(16);
    
    const decipher = crypto.createDecipheriv('aes-256-cbc', KEY, iv);
    let decrypted = decipher.update(ct, '', 'utf8');
    decrypted += decipher.final('utf8');
    return decrypted;
  } catch (e) {
    return null;
  }
}

export default function handler(req, res) {
  const { data } = req.query;

  if (!data) {
    return res.status(400).send('Bad request');
  }

  const targetUrl = decryptToken(data);

  if (!targetUrl) {
    return res.status(403).send('Access denied: Invalid token');
  }

  res.setHeader('Cache-Control', 'no-store');
  return res.redirect(302, targetUrl);
}
