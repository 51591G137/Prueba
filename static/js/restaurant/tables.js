/* Mesas: lista con su estado (libre/ocupada), alta, edición y borrado. */
import { api } from '../core/api.js';
import { field, fill, h, loading } from '../core/dom.js';
import { people } from '../core/format.js';
import { leave } from '../core/router.js';
import { confirmDialog, guarded, onSubmit, setScreen, toast } from '../core/ui.js';
import { tableChip } from './status.js';

export async function tablesTab({ uid, rid, box, stale }) {
  const list = h('ul', { class: 'list' });

  async function refresh() {
    const tables = await api.get(`/api/restaurants/${rid}/tables`);
    if (stale()) return;
    fill(
      list,
      tables,
      (table) =>
        h(
          'li',
          null,
          h(
            'div',
            { class: 'row' },
            h(
              'a',
              { class: 'main', href: `#/u/${uid}/r/${rid}/mesa/${table.id}` },
              h('strong', null, table.name),
              h('div', { class: 'muted small' }, people(table.capacity)),
            ),
            tableChip(table.status),
            h('a', { class: 'btn small secondary', href: `#/u/${uid}/r/${rid}/mesa/${table.id}/editar`, 'aria-label': `Editar ${table.name}` }, 'Editar'),
          ),
        ),
      'Este restaurante aún no tiene mesas. Añade la primera abajo.',
    );
  }

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data, f) => {
        await api.post(`/api/restaurants/${rid}/tables`, data);
        f.reset();
        toast('Mesa añadida');
        await refresh();
      }),
    },
    h('h2', null, 'Nueva mesa'),
    h(
      'div',
      { class: 'pair' },
      field('Nombre', h('input', { name: 'name', type: 'text', required: true, maxlength: 40, placeholder: 'Mesa 1', autocomplete: 'off' })),
      field('Personas', h('input', { name: 'capacity', type: 'number', required: true, min: 1, max: 50, value: 4, inputmode: 'numeric' })),
    ),
    h('button', { class: 'btn', type: 'submit' }, 'Añadir mesa'),
  );

  box.append(list, form);
  await refresh();
}

export async function viewTableEdit({ params, stale }) {
  const { uid, rid, tid } = params;
  const back = `#/u/${uid}/r/${rid}/mesas`;
  setScreen('Editar mesa', back, loading());
  const table = await api.get(`/api/tables/${tid}`);
  if (stale()) return;

  const form = h(
    'form',
    {
      class: 'panel',
      onsubmit: onSubmit(async (data) => {
        await api.patch(`/api/tables/${tid}`, data);
        toast('Cambios guardados');
        leave(back);
      }),
    },
    h('h2', null, table.name),
    h(
      'div',
      { class: 'pair' },
      field('Nombre', h('input', { name: 'name', type: 'text', value: table.name, required: true, maxlength: 40, autocomplete: 'off' })),
      field('Personas', h('input', { name: 'capacity', type: 'number', value: table.capacity, required: true, min: 1, max: 50, inputmode: 'numeric' })),
    ),
    h('button', { class: 'btn', type: 'submit' }, 'Guardar cambios'),
  );

  const occupied = table.status === 'ocupada';
  const remove = guarded(async () => {
    const confirmed = await confirmDialog({
      title: `¿Borrar ${table.name}?`,
      message: table.reservations
        ? `También se borrarán sus reservas (${table.reservations}). Las facturas ya cobradas se conservan. No se puede deshacer.`
        : 'Las facturas ya cobradas se conservan. No se puede deshacer.',
      confirmLabel: 'Borrar mesa',
      danger: true,
    });
    if (!confirmed) return;
    await api.del(`/api/tables/${tid}`);
    toast('Mesa borrada');
    leave(back);
  });

  setScreen(
    'Editar mesa',
    back,
    form,
    h(
      'div',
      { class: 'danger-zone' },
      occupied && h('p', { class: 'muted' }, 'No se puede borrar mientras esté ocupada: cobra o borra antes sus comandas.'),
      h('button', { class: 'btn danger', type: 'button', disabled: occupied, onclick: remove }, 'Borrar mesa'),
    ),
  );
}
