<?php
$cache = __DIR__ . '/offres.json';
$data = file_exists($cache) ? json_decode(file_get_contents($cache), true) : null;
$structures = $data['structures'] ?? [];
$generatedAt = $data['generated_at'] ?? null;
?>
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Offres d'emploi - filiales</title>
<style>
body { font-family: sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #ddd; }
.meta { color: #666; font-size: 0.9rem; }
</style>
</head>
<body>
<h1>Offres d'emploi des filiales</h1>
<?php if ($generatedAt): ?>
<p class="meta">Donnees generees le <?= htmlspecialchars($generatedAt) ?></p>
<?php endif; ?>

<?php if (empty($structures)): ?>
<p>Aucune donnee disponible. Lancer <code>scan_siaes.py</code> pour generer le cache.</p>
<?php else: ?>
<table>
<thead>
<tr><th>Structure</th><th>Ville</th><th>Postes ouverts</th><th>Intitules</th></tr>
</thead>
<tbody>
<?php foreach ($structures as $s): ?>
<tr>
<td><?= htmlspecialchars($s['raison_sociale']) ?></td>
<td><?= htmlspecialchars($s['ville']) ?></td>
<td><?= (int)$s['nb_postes_ouverts'] ?></td>
<td><?= htmlspecialchars(implode(', ', $s['postes'])) ?></td>
</tr>
<?php endforeach; ?>
</tbody>
</table>
<?php endif; ?>
</body>
</html>
