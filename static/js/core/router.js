/* Router por hash (#/ruta). Cada pantalla tiene su propia dirección, así que el botón «Atrás»
   del móvil vuelve a la pantalla anterior y, si se recarga la página, se queda en la misma.

   Las rutas son pares [patrón, vista]:
     ['u/:uid/r/:rid/:tab?', viewRestaurant]   ':nombre' captura un trozo; '?' lo hace opcional (solo el último)
   La vista recibe { params, stale }; stale() es true si ya se ha navegado a otra pantalla,
   para no pintar respuestas tardías encima de la pantalla nueva. */
import { dismissDialog, showError } from './ui.js';

function compile(pattern) {
  const segments = pattern.split('/').filter(Boolean);
  const optionalLast = segments.length > 0 && segments[segments.length - 1].endsWith('?');
  const required = optionalLast ? segments.length - 1 : segments.length;
  return (parts) => {
    if (parts.length < required || parts.length > segments.length) return null;
    const params = {};
    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i];
      if (segment.startsWith(':')) {
        if (parts[i] !== undefined) params[segment.slice(1).replace('?', '')] = decodeURIComponent(parts[i]);
      } else if (parts[i] !== segment) {
        return null;
      }
    }
    return params;
  };
}

let current = 0;

export function startRouter(routes) {
  const compiled = routes.map(([pattern, view]) => [compile(pattern), view]);

  async function render() {
    const id = ++current;
    const stale = () => id !== current;
    dismissDialog();
    const path = location.hash.replace(/^#\/?/, '').split('?')[0];
    const parts = path.split('/').filter(Boolean);
    for (const [match, view] of compiled) {
      const params = match(parts);
      if (params) {
        try {
          await view({ params, stale });
        } catch (err) {
          if (!stale()) showError(err);
        }
        return;
      }
    }
    navigate('#/', { replace: true }); // dirección desconocida: al inicio
  }

  window.addEventListener('hashchange', render);
  render();
}

export function navigate(hash, { replace = false } = {}) {
  if (replace) location.replace(hash);
  else location.hash = hash;
}

/* Sale de una pantalla de edición: vuelve a la anterior del historial (que se vuelve a cargar sola).
   Si no hay historial (se abrió la dirección directamente), va a la pantalla de respaldo. */
export function leave(fallbackHash) {
  if (history.length > 1) history.back();
  else navigate(fallbackHash, { replace: true });
}
