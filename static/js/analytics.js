(() => {
  function drawRevenue() {
    const canvas = document.getElementById('revenue-chart');
    const data = document.getElementById('revenue-data');
    if (!canvas || !data || !window.Chart) return;
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();
    const values = JSON.parse(data.textContent);
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(37, 99, 235, .16)');
    gradient.addColorStop(1, 'rgba(37, 99, 235, 0)');
    const money = value => new Intl.NumberFormat('vi-VN').format(value) + ' ₫';
    new Chart(canvas, {type: 'line', data: {labels: values.labels, datasets: [
      {label: 'Doanh thu', data: values.revenue, borderColor: '#2563eb', backgroundColor: gradient, fill: true, tension: .35, borderWidth: 2.5, pointRadius: values.labels.length > 60 ? 0 : 2, pointHoverRadius: 5},
      {label: 'Tiền đã thu', data: values.receipts, borderColor: '#28b5a3', fill: false, tension: .35, borderWidth: 2, borderDash: [5, 4], pointRadius: 0, pointHoverRadius: 4}
    ]}, options: {responsive: true, maintainAspectRatio: false, interaction: {mode: 'index', intersect: false}, plugins: {legend: {display: false}, tooltip: {backgroundColor: '#172b4d', padding: 12, callbacks: {label: item => item.dataset.label + ': ' + money(item.parsed.y)}}}, scales: {x: {grid: {display: false}, border: {display: false}, ticks: {color: '#8a96a8', maxTicksLimit: 8, maxRotation: 0}}, y: {beginAtZero: true, border: {display: false}, grid: {color: '#f0f3f7'}, ticks: {color: '#8a96a8', maxTicksLimit: 5, callback: value => value >= 1000000 ? (value / 1000000).toLocaleString('vi-VN') + 'tr' : value >= 1000 ? (value / 1000).toLocaleString('vi-VN') + 'k' : value}}}, animation: {duration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 450}}});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', drawRevenue);
  else drawRevenue();
  document.addEventListener('htmx:afterSettle', drawRevenue);
})();
