export default function handler(req, res) {
  const targetUrl = req.query.url;

  if (!targetUrl) {
    return res.status(400).send('Bad request: missing url');
  }

  // Мгновенный 302-редирект на ваш спейс (или конечный прокси), без нагрузки на Vercel
  res.setHeader('Cache-Control', 'no-store');
  return res.redirect(302, targetUrl);
}
