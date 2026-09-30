export default function handler(req, res) {
  const targetUrl = req.query.url;

  if (!targetUrl) {
    return res.status(400).send('Bad request: missing url');
  }

  // Перенаправляем на ваш Hugging Face Space
  const finalDest = `https://stream-tv-digital.hf.space/${targetUrl}`;

  res.setHeader('Cache-Control', 'no-store');
  return res.redirect(302, finalDest);
}
