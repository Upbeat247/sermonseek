// Optional: Netlify scheduled function for daily push notifications (v2, not shipped in MVP).
// To enable: install web-push, store subscriptions in Netlify Blobs, schedule via netlify.toml.
export default async () => {
  return new Response("Daily push not yet configured", { status: 200 });
};

export const config = {
  // schedule: "@daily",   // uncomment to enable
};
