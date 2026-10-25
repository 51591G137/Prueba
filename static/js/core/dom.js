/* Crear elementos del DOM sin escribir HTML a mano.
   Los textos se insertan siempre como texto, nunca como HTML: lo que escriba un usuario
   (un nombre, una nota...) no puede romper la página. */

export const $ = (selector, root = document) => root.querySelector(selector);

/* h('a', { class: 'btn', href: '#/x', onclick: fn }, 'Texto', otroElemento) */
export function h(tag, props, ...children) {
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

/* Sustituye el contenido de un elemento ignorando los valores vacíos (null/false), que replaceChildren pintaría como texto. */
export function replace(el, ...children) {
  el.replaceChildren(...children.flat(Infinity).filter((child) => child != null && child !== false));
}

export const field = (label, input) => h('label', null, label, input);
export const empty = (text) => h('li', { class: 'empty' }, text);
export const loading = () => h('p', { class: 'muted' }, 'Cargando…');

/* Rellena una lista <ul> con una fila por elemento (o con el mensaje de lista vacía). */
export function fill(listEl, items, render, emptyText) {
  listEl.replaceChildren(...(items.length ? items.map(render) : [empty(emptyText)]));
}

export function listOf(items, render, emptyText, className = 'list') {
  const listEl = h('ul', { class: className });
  fill(listEl, items, render, emptyText);
  return listEl;
}
