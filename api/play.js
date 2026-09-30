export default function handler(req, res) {
  const targetUrl = req.query.url;

  if (!targetUrl) {
    return res.status(400).send('Bad request: missing url');
  }

  // Обязательно оставляем /proxy, так как бэкенд на спейсе ждет его
  const finalDest = `https://stream-tv-digital.hf.space/proxy?url=${encodeURIComponent(targetUrl)}`;

  res.setHeader('Cache-Control', 'no-store');
  return res.redirect(302, finalDest);
}
