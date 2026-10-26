/* A portal's two source-backed classification axes; original values remain query keys. */
(function () {
  var node = document.getElementById('charts'), data = node ? JSON.parse(node.textContent || '{}') : {};
  if (!data.landscape) return;
  var rows = new Map(data.landscape.rows.map(function (row) { return [row.id, row]; }));
  var fields = { 'molecular-type': 'molecular_types', 'mechanism-class': 'mechanism_classes' };
  var labels = data.landscape.classification_labels || {};
  function el(id) { return document.getElementById(id); }
  function label(field, value) { return labels[field] && labels[field][value] || value; }
  function refresh() {
    var title = el('landscape-group-title');
    if (title) title.textContent = window.CIW_CLASSIFICATION.title() + ' × 全球阶段记录';
    var filter = document.querySelector('input[data-filter="tbl-a"]');
    if (filter) filter.dispatchEvent(new Event('input', { bubbles: true }));
  }
  Object.keys(fields).forEach(function (id) {
    var select = el(id), field = fields[id];
    if (!select) return;
    Array.from(new Set(data.landscape.rows.flatMap(function (row) { return row[field] || []; }))).sort().forEach(function (value) {
      var option = document.createElement('option');
      option.value = value; option.textContent = label(field, value); select.appendChild(option);
    });
    select.addEventListener('change', refresh);
  });
  var grouping = el('landscape-group');
  if (grouping) grouping.addEventListener('change', refresh);
  window.CIW_CLASSIFICATION = {
    matches: function (id) {
      var row = rows.get(id);
      return row && Object.keys(fields).every(function (key) {
        var select = el(key);
        return !select || select.value === 'all' || (row[fields[key]] || []).includes(select.value);
      });
    },
    groups: function (row) {
      var field = grouping ? grouping.value : 'targets';
      return (row[field] || []).map(function (value) { return label(field, value); });
    },
    title: function () {
      return { targets: '靶点', molecular_types: '分子类型', mechanism_classes: '机制类别' }[grouping ? grouping.value : 'targets'];
    }
  };
})();
