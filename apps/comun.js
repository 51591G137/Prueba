'use strict';
/* Utilidades compartidas por la app de restaurantes y la de clientes.
   Sin dependencias ni paso de compilación: Flask lo sirve tal cual. */

const $ = (selector) => document.querySelector(selector);

/* Crea un elemento DOM. Los textos se insertan como texto, nunca como HTML,
   así que lo que escriba un usuario no puede romper la página. */
function h(tag, props, ...children) {
  const el = document.createElement(tag);
  let value;
  for (const [key, val] of Object.entries(props || {})) {
    if (val === false || val == null) continue;
    if (key === 'value') {
      value = val; // se asigna al final: un <select> necesita antes sus <option>
      if (tag !== 'select') el.setAttribute('value', val); // valor por defecto, para que form.reset() lo conserve
    } else if (key.startsWith('on')) el.addEventListener(key.slice(2), val);
    else if (key === 'class') el.className = val;
    else el.setAttribute(key, val === true ? '' : val);
  }
  el.append(...children.flat(Infinity).filter((child) => child != null && child !== false));
  if (value !== undefined) el.value = value;
  return el;
}

/* ---------- API ---------- */

async function api(path, { method = 'GET', body } = {}) {
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

/* ---------- Avisos y formularios ---------- */

function toast(message, isError = false) {
  const previous = $('.toast');
  if (previous) previous.remove();
  const el = h('div', { class: isError ? 'toast error' : 'toast', role: 'status' }, message);
  document.body.append(el);
  setTimeout(() => el.remove(), isError ? 5000 : 3000);
}

/* Envoltorio para formularios: evita el doble envío y enseña los errores como aviso.
   El manejador recibe los campos como objeto ({name: '...', capacity: '4'}) y el formulario. */
function onSubmit(handler) {
  return async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button[type=submit]');
    button.disabled = true;
    try {
      await handler(Object.fromEntries(new FormData(form)), form);
    } catch (err) {
      toast(err.message, true);
    } finally {
      button.disabled = false;
    }
  };
}

const field = (label, input) => h('label', null, label, input);
const empty = (text) => h('li', { class: 'empty' }, text);
const loading = () => h('p', { class: 'muted' }, 'Cargando…');

/* ---------- Fechas, horas e importes ---------- */

const euro = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });
const people = (n) => `${n} ${n === 1 ? 'persona' : 'personas'}`;

/* Fecha de hoy en la zona horaria del dispositivo, como AAAA-MM-DD. */
function todayStr() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function formatDate(iso) {
  const [year, month, day] = iso.split('-');
  return `${day}/${month}/${year}`;
}

/* Franjas de media hora, de 08:00 a 23:30. */
function timeSlots() {
  const slots = [];
  for (let hour = 8; hour < 24; hour++) {
    for (const minutes of ['00', '30']) slots.push(`${String(hour).padStart(2, '0')}:${minutes}`);
  }
  return slots;
}

/* Desplegable de horas. Con allLabel añade una primera opción «sin filtro» (valor vacío). */
function timeSelect(value, allLabel) {
  const options = timeSlots().map((slot) => h('option', { value: slot }, slot));
  if (allLabel) options.unshift(h('option', { value: '' }, allLabel));
  return h('select', { name: 'time', value }, options);
}

/* ---------- Pantallas ---------- */

/* Cambia título, flecha de volver (backHref = null la oculta) y contenido. */
function setScreen(title, backHref, ...content) {
  $('#title').textContent = title;
  const back = $('#back');
  back.hidden = !backHref;
  if (backHref) back.setAttribute('href', backHref);
  $('#app').replaceChildren(...content.flat(Infinity).filter(Boolean));
  window.scrollTo(0, 0);
}

function showError(err) {
  setScreen(
    'No se pudo cargar',
    '#/',
    h(
      'div',
      { class: 'notice' },
      h('p', null, err.message),
      h('button', { class: 'btn', type: 'button', onclick: () => location.reload() }, 'Reintentar'),
    ),
  );
}

/* Pestañas. Cambiar de pestaña reemplaza la entrada del historial en lugar de añadir otra,
   así «Atrás» sale del restaurante en vez de recorrer las pestañas una a una. */
function tabBar(base, tabs, active) {
  return h(
    'nav',
    { class: 'tabs' },
    tabs.map(([key, label]) =>
      h(
        'a',
        {
          href: `${base}/${key}`,
          class: key === active ? 'active' : false,
          'aria-current': key === active ? 'page' : false,
          onclick: (event) => {
            event.preventDefault();
            location.replace(`${base}/${key}`);
          },
        },
        label,
      ),
    ),
  );
}

/* Lista del menú (la carta): plato ..... precio, con la descripción debajo. */
function menuList(items, emptyText) {
  if (!items.length) return h('ul', { class: 'list' }, empty(emptyText));
  return h(
    'ul',
    { class: 'carta' },
    items.map((item) =>
      h(
        'li',
        null,
        h(
          'div',
          { class: 'carta-line' },
          h('span', { class: 'dish' }, item.name),
          h('span', { class: 'leader', 'aria-hidden': 'true' }),
          h('span', { class: 'price' }, euro.format(item.price)),
        ),
        item.description && h('p', { class: 'desc' }, item.description),
      ),
    ),
  );
}

/* ---------- Router por hash ---------- */
/* Cada pantalla tiene su propia dirección (#/u/3/r/7/menu). Así el botón «Atrás» del móvil
   vuelve a la pantalla anterior y, si se recarga la página, se queda en la misma. */

let currentView = 0;

function startRouter(dispatch) {
  async function render() {
    const view = ++currentView;
    const isStale = () => view !== currentView; // true si ya se ha navegado a otra pantalla
    const parts = location.hash.replace(/^#\/?/, '').split('/').filter(Boolean);
    try {
      await dispatch(parts, isStale);
    } catch (err) {
      if (!isStale()) showError(err);
    }
  }
  window.addEventListener('hashchange', render);
  render();
}
