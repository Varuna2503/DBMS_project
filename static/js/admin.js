(function () {
  // ---- Mobile sidebar ----
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('backdrop');
  const toggle = (open) => {
    sidebar.classList.toggle('open', open);
    backdrop.classList.toggle('open', open);
  };
  document.getElementById('menuBtn')?.addEventListener('click', () => toggle(true));
  backdrop?.addEventListener('click', () => toggle(false));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') toggle(false); });

  // ---- Table search + filters ----
  // Search input:  <input data-filter-for="tableId" data-filter-type="search">
  // Select filter: <select data-filter-for="tableId" data-filter-key="status">
  // Rows:          <tr data-row data-status="..."> and a <tr class="no-match"> for empty results
  function applyFilters(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    const controls = document.querySelectorAll(`[data-filter-for="${tableId}"]`);
    const rows = table.querySelectorAll('tbody tr[data-row]');
    let visible = 0;
    rows.forEach((row) => {
      let show = true;
      controls.forEach((c) => {
        const val = c.value.trim().toLowerCase();
        if (!val) return;
        if (c.dataset.filterType === 'search') {
          if (!row.textContent.toLowerCase().includes(val)) show = false;
        } else if ((row.dataset[c.dataset.filterKey] || '').toLowerCase() !== val) {
          show = false;
        }
      });
      row.hidden = !show;
      if (show) visible++;
    });
    const none = table.querySelector('.no-match');
    if (none) none.style.display = rows.length && !visible ? 'table-row' : 'none';
  }
  document.querySelectorAll('[data-filter-for]').forEach((c) => {
    const run = () => applyFilters(c.dataset.filterFor);
    c.addEventListener('input', run);
    c.addEventListener('change', run);
  });

  // ---- Form validation (inline messages) ----
  // Forms opt in with data-validate-form. Inputs may set data-validate="phone".
  function validateField(input) {
    const field = input.closest('.field');
    const v = input.value.trim();
    let msg = '';
    if (input.required && !v) {
      msg = input.dataset.requiredMsg || 'This field is required.';
    } else if (input.dataset.validate === 'phone' && v && !/^\d{10}$/.test(v)) {
      msg = 'Enter exactly 10 digits, numbers only.';
    } else if (v && !input.checkValidity()) {
      msg = input.dataset.rangeMsg || 'Enter a valid value.';
    }
    if (field) {
      field.classList.toggle('invalid', !!msg);
      const err = field.querySelector('.field-error');
      if (err) err.textContent = msg;
    }
    return !msg;
  }
  document.querySelectorAll('form[data-validate-form]').forEach((form) => {
    form.setAttribute('novalidate', '');
    const inputs = form.querySelectorAll('.input');
    inputs.forEach((i) => {
      i.addEventListener('blur', () => validateField(i));
      i.addEventListener('input', () => { if (i.closest('.field')?.classList.contains('invalid')) validateField(i); });
    });
    form.addEventListener('submit', (e) => {
      let ok = true;
      let first = null;
      inputs.forEach((i) => { if (!validateField(i)) { ok = false; first = first || i; } });
      if (!ok) { e.preventDefault(); first.focus(); }
    });
  });
})();
