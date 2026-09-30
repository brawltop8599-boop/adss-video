import crypto from 'crypto';

export default function handler(req, res) {
  const { data } = req.query;

  if (!data) {
    return res.status(400).send('Bad request');
  }

  try {
    // Получаем секретный ключ из переменных окружения Vercel
    const secretKey = process.env.SECRET_KEY || 'MySuperSecretKey2026_ChangeMe3222';
    
    // Приводим ключ к ровно 32 байтам
    const keyBuffer = Buffer.alloc(32);
    Buffer.from(secretKey).copy(keyBuffer);

    // Восстанавливаем символы base64url обратно в стандартный base64
    let base64 = data.replace(/-/g, '+').replace(/_/g, '/');
    while (base64.length % 4) {
      base64 += '=';
    }

    const iv_ct = Buffer.from(base64, 'base64');
    const iv = iv_ct.slice(0, 16);
    const ct = iv_ct.slice(16);
    
    const decipher = crypto.createDecipheriv('aes-256-cbc', keyBuffer, iv);
    let decrypted = decipher.update(ct, 'binary', 'utf8');
    decrypted += decipher.final('utf8');

    // Мгновенный 302 редирект на оригинальный поток (сервер не качает видео, трафик идет напрямую)
    res.setHeader('Cache-Control', 'no-store');
    return res.redirect(302, decrypted);

  } catch (e) {
    return res.status(403).send('Access denied: Invalid token');
  }
}
