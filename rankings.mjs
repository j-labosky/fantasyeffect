import { getStore } from "@netlify/blobs";

const STORE_NAME = "rankings";

// Extract user role from Netlify Identity JWT
function getUserRole(authHeader) {
  if (!authHeader || !authHeader.startsWith("Bearer ")) return null;
  try {
    const token = authHeader.split(" ")[1];
    const payload = JSON.parse(
      Buffer.from(token.split(".")[1], "base64").toString()
    );
    const roles = payload?.app_metadata?.roles || [];
    const hierarchy = { starter: 1, degenerate: 2, owner: 3 };
    let highest = "starter";
    let highestLevel = 0;
    for (const r of roles) {
      const lvl = hierarchy[r.toLowerCase()] || 0;
      if (lvl > highestLevel) {
        highestLevel = lvl;
        highest = r.toLowerCase();
      }
    }
    return highest;
  } catch {
    return null;
  }
}

export default async (req, context) => {
  const url = new URL(req.url);
  const format = url.searchParams.get("format") || "sf";

  // Validate format
  const validFormats = ["sf", "oneqb", "twoqb", "twote"];
  if (!validFormats.includes(format)) {
    return new Response(JSON.stringify({ error: "Invalid format" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const store = getStore({ name: STORE_NAME, consistency: "strong" });
  const blobKey = `edits_${format}`;

  // ── GET: return shared edits (anyone can read) ──
  if (req.method === "GET") {
    try {
      const data = await store.get(blobKey, { type: "json" });
      return new Response(JSON.stringify(data || null), {
        headers: { "Content-Type": "application/json" },
      });
    } catch {
      return new Response(JSON.stringify(null), {
        headers: { "Content-Type": "application/json" },
      });
    }
  }

  // ── POST: save edits (owner only) ──
  if (req.method === "POST") {
    const role = getUserRole(req.headers.get("authorization"));
    if (role !== "owner") {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      });
    }

    try {
      const body = await req.json();
      body.savedAt = new Date().toISOString();
      await store.setJSON(blobKey, body);
      return new Response(JSON.stringify({ ok: true }), {
        headers: { "Content-Type": "application/json" },
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
  }

  // ── DELETE: reset edits (owner only) ──
  if (req.method === "DELETE") {
    const role = getUserRole(req.headers.get("authorization"));
    if (role !== "owner") {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      });
    }

    try {
      await store.delete(blobKey);
      return new Response(JSON.stringify({ ok: true }), {
        headers: { "Content-Type": "application/json" },
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
  }

  return new Response("Method not allowed", { status: 405 });
};
