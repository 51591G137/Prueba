/* Piezas de interfaz comunes: pantallas, avisos, formularios, pestañas y diálogo de confirmación. */
import { $, h } from './dom.js';

/* ---------- Pantallas ---------- */

/* Cambia el título, la flecha de volver (backHref = null la oculta) y el contenido. */
export function setScreen(title, backHref, ...content) {
  $('#title').textContent = title;
  const back = $('#back');
  back.hidden = !backHref;
  if (backHref) back.setAttribute('href', backHref);
  $('#app').replaceChildren(...content.flat(Infinity).filter(Boolean));
  window.scrollTo(0, 0);
}

export function showError(err) {
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
export function tabBar(base, tabs, active) {
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

/* ---------- Avisos y formularios ---------- */

export function toast(message, isError = false) {
  const previous = $('.toast');
  if (previous) previous.remove();
  const el = h('div', { class: isError ? 'toast error' : 'toast', role: 'status' }, message);
  document.body.append(el);
  setTimeout(() => el.remove(), isError ? 5000 : 3000);
}

/* Envoltorio para formularios: evita el doble envío y enseña los errores como aviso.
   El manejador recibe los campos como objeto ({name: '...', capacity: '4'}) y el formulario. */
export function onSubmit(handler) {
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

/* Botón que ejecuta una acción con control de errores y sin doble pulsación. */
export function guarded(action) {
  return async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      await action();
    } catch (err) {
      toast(err.message, true);
    } finally {
      button.disabled = false;
    }
  };
}

/* ---------- Diálogo de confirmación ---------- */

let openDialog = null;

/* Pregunta antes de una acción importante. Devuelve true si la persona acepta. */
export function confirmDialog({ title, message, confirmLabel = 'Aceptar', danger = false }) {
  dismissDialog();
  return new Promise((resolve) => {
    const close = (result) => {
      if (openDialog !== dialog) return;
      openDialog = null;
      dialog.close();
      dialog.remove();
      resolve(result);
    };
    const dialog = h(
      'dialog',
      { 'aria-labelledby': 'dialog-title' },
      h('h2', { id: 'dialog-title' }, title),
      h('p', null, message),
      h(
        'div',
        { class: 'dialog-actions' },
        h('button', { class: 'btn secondary', type: 'button', onclick: () => close(false) }, 'Volver'),
        h('button', { class: danger ? 'btn danger' : 'btn', type: 'button', onclick: () => close(true) }, confirmLabel),
      ),
    );
    dialog.addEventListener('cancel', (event) => {
      event.preventDefault();
      close(false);
    });
    dialog.dismiss = () => close(false);
    document.body.append(dialog);
    openDialog = dialog;
    dialog.showModal();
  });
}

/* Cierra el diálogo abierto (al cambiar de pantalla, por ejemplo con el botón «Atrás»). */
export function dismissDialog() {
  if (openDialog) openDialog.dismiss();
}
