# Local frontend dependencies

These pinned files are served locally. The application makes no runtime request to a CDN.

| File | Version | Official upstream / distribution | License |
| --- | --- | --- | --- |
| htmx.min.js | 2.0.8 | https://github.com/bigskysoftware/htmx / https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js | BSD 2-Clause, HTMX-LICENSE.txt |
| chart.umd.js | 4.5.1 | https://github.com/chartjs/Chart.js / https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js | MIT, CHARTJS-LICENSE.md |

Tailwind CSS 4.3.3 is compiled from `assets/css/tailwind.css` to `static/css/tailwind.css` with `scripts/build_css.ps1`. The compiled file is checked in so Python-only setups do not need Node or Tailwind to run the web application.
