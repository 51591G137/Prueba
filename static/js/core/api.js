/* Llamadas al servidor. Todas devuelven el JSON o lanzan un Error con un mensaje legible. */

async function request(path, { method = 'GET', body } = {}) {
  let res;
  try {
    res = await fetch(path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    throw new Error('No hay conexión con el servidor. Comprueba tu conexión e inténtalo de nuevo.');
  }
  let data = null;
  try {
    data = await res.json();
  } catch (err) {
    /* la respuesta no traía JSON */
  }
  if (!res.ok) {
    throw new Error((data && data.error) || `El servidor respondió con un error (${res.status}). Inténtalo de nuevo.`);
  }
  return data;
}

export const api = {
  get: (path) => request(path),
  post: (path, body = {}) => request(path, { method: 'POST', body }),
  patch: (path, body = {}) => request(path, { method: 'PATCH', body }),
  del: (path) => request(path, { method: 'DELETE' }),
};
