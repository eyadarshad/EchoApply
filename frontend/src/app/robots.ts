import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/audit/cv", "/audit/linkedin", "/tailor", "/cover-letter", "/interview"],
        disallow: ["/api/", "/settings"],
      },
    ],
    sitemap: "https://echoapply.ai/sitemap.xml",
  };
}
