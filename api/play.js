{
  "rewrites": [
    {
      "source": "/http/:path*",
      "destination": "/api/play?url=http://:path*"
    },
    {
      "source": "/https/:path*",
      "destination": "/api/play?url=https://://:path*"
    }
  ]
}
