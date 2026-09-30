import crypto from 'crypto';

export default async function handler(req, res) {
  const { data } = req.query;

  if (!data) {
    return res.status(400).send('Bad request');
  }

  try {
    // 1. Расшифровываем ссылку
    const secretKey = process.env.SECRET_KEY || 'MySuperSecretKey2026_ChangeMe3222';
    const keyBuffer = Buffer.alloc(32);
    Buffer.from(secretKey).copy(keyBuffer);

    let base64 = data.replace(/-/g, '+').replace(/_/g, '/');
    while (base64.length % 4) {
      base64 += '=';
    }

    const iv_ct = Buffer.from(base64, 'base64');
    const iv = iv_ct.slice(0, 16);
    const ct = iv_ct.slice(16);
    
    const decipher = crypto.createDecipheriv('aes-256-cbc', keyBuffer, iv);
    let targetUrl = decipher.update(ct, 'binary', 'utf8');
    targetUrl += decipher.final('utf8');

    // 2. Проксируем запрос к реальному источнику скрытно от клиента
    const response = await fetch(targetUrl, {
      headers: {
        'User-Agent': req.headers['user-agent'] || 'Vercel-IPTV-Proxy'
      }
    });

    if (!response.ok) {
      return res.status(response.status).send('Stream error from source');
    }

    // Передаем заголовки и контент потока обратно плееру
    res.setHeader('Content-Type', response.headers.get('content-type') || 'video/mp2t');
    res.setHeader('Cache-Control', 'no-cache');

    // Стримим данные клиенту
    const reader = response.body.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      res.write(value);
    }
    res.end();

  } catch (e) {
    return res.status(403).send('Access denied or proxy error');
  }
}
