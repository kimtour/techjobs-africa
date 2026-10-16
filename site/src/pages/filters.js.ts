// Keep already-open pages using the original script URL working after updates.
import script from "../scripts/filters.js?raw";

export function GET() {
  return new Response(script, {
    headers: { "Content-Type": "application/javascript; charset=utf-8" },
  });
}
