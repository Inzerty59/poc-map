<?php
/**
 * Plugin Name: Offres Emploi Filiales
 * Description: Affiche les offres d'emploi des filiales (SIAE) via shortcode [offres_emploi], avec carte Leaflet.
 */

if (!defined('ABSPATH')) {
    exit;
}

function offres_emploi_get_data() {
    $cache = __DIR__ . '/offres.json';
    if (!file_exists($cache)) {
        return [];
    }
    $data = json_decode(file_get_contents($cache), true);
    return $data['structures'] ?? [];
}

function offres_emploi_shortcode() {
    $structures = offres_emploi_get_data();
    if (empty($structures)) {
        return '<p>Aucune offre trouvee.</p>';
    }

    wp_enqueue_style('leaflet', 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css', [], '1.9.4');
    wp_enqueue_script('leaflet', 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js', [], '1.9.4', true);

    $points = array_values(array_filter($structures, fn($s) => !empty($s['lat']) && !empty($s['lon'])));

    ob_start();
    ?>
    <div id="offres-emploi-map" style="height:400px;margin-bottom:1.5rem;"></div>

    <style>
        .offres-emploi-table .offre-detail { margin-bottom: 0.4rem; cursor: pointer; }
        .offres-emploi-table .offre-detail summary { font-weight: 600; }
        .offres-emploi-table .offre-detail[open] summary { margin-bottom: 0.3rem; }
    </style>

    <table class="offres-emploi-table">
        <thead>
            <tr>
                <th>Structure</th>
                <th>Ville</th>
                <th>Postes ouverts</th>
                <th>Intitules</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($structures as $s): ?>
            <tr>
                <td><?= esc_html($s['raison_sociale']) ?></td>
                <td><?= esc_html($s['ville']) ?></td>
                <td><?= (int) $s['nb_postes_ouverts'] ?></td>
                <td>
                    <?php foreach ($s['postes'] as $poste): ?>
                        <details class="offre-detail">
                            <summary><?= esc_html($poste['titre']) ?></summary>
                            <p><strong><?= esc_html($poste['type_contrat']) ?></strong> &middot; <?= esc_html($poste['lieu']) ?></p>
                            <p><?= nl2br(esc_html($poste['description'])) ?></p>
                        </details>
                    <?php endforeach; ?>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>

    <script>
    document.addEventListener('DOMContentLoaded', function () {
        var points = <?= wp_json_encode($points) ?>;
        var map = L.map('offres-emploi-map');
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(map);

        if (points.length === 0) {
            map.setView([46.6, 2.5], 5); // centre France
            return;
        }

        var bounds = [];
        points.forEach(function (p) {
            var marker = L.marker([p.lat, p.lon]).addTo(map);
            var postes = p.postes.length ? '<ul>' + p.postes.map(function (t) { return '<li>' + t.titre + '</li>'; }).join('') + '</ul>' : '<p>Aucun poste ouvert</p>';
            marker.bindPopup('<strong>' + p.raison_sociale + '</strong><br>' + p.ville + '<br>' + postes);
            bounds.push([p.lat, p.lon]);
        });
        map.fitBounds(bounds, { padding: [30, 30], maxZoom: 13 });
    });
    </script>
    <?php
    return ob_get_clean();
}
add_shortcode('offres_emploi', 'offres_emploi_shortcode');
