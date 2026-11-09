const fs = require('fs');
const path = require('path');
const xlsx = require('xlsx');

function loadAndParse(filename, sheetName) {
    if (!fs.existsSync(filename)) {
        console.log("File not found:", filename);
        return [];
    }
    const wb = xlsx.readFile(filename);
    const sheet = wb.Sheets[sheetName];
    if (!sheet) {
        throw new Error(`Sheet "${sheetName}" not found in ${filename} (available: ${wb.SheetNames.join(', ')})`);
    }
    const rawData = xlsx.utils.sheet_to_json(sheet);

    const parsedData = [];

    // Start from index 1 to skip the header row, it seems row 0 is english mapping
    for (let i = 1; i < rawData.length; i++) {
        const row = rawData[i];

        let rawKp = row['meters'];
        let rawLat = row['Latitude'];
        let rawLng = row['Longitude'] || row['Longitude '];
        let rawDepth = row['Depth of wall loss'];
        let rawPof = row['Probability of failure'];

        if (rawLat === undefined || rawLng === undefined) continue;

        const kp = parseFloat(rawKp) || 0;
        const latVal = parseFloat(rawLat);
        const lngVal = parseFloat(rawLng);

        if (isNaN(latVal) || isNaN(lngVal)) continue;

        const depth = parseFloat(rawDepth) || 0;
        const pof = parseFloat(rawPof) || 0;
        const nomThickness = parseFloat(row['Nominal thickness']) || 12.7;

        let type = row['Comments or notes'] || row['Comments or notes to display when clicking + in the table'] || "N/A";

        let severity = "Basso";
        if (pof >= 0.8) severity = "Critico";
        else if (pof >= 0.5) severity = "Alto";
        else if (pof >= 0.2) severity = "Moderato";

        parsedData.push({
            id: `KP-${kp}`,
            position: [lngVal, latVal],
            kp: kp,
            pof: parseFloat(pof.toFixed(3)),
            depth: parseFloat(depth.toFixed(2)),
            nomThickness: nomThickness,
            severity: severity,
            type: String(type)
        });
    }

    return parsedData;
}

function run() {
    // Percorsi sovrascrivibili via argomenti CLI o variabili d'ambiente
    const chileFile = process.argv[2] || process.env.CHILE_XLSX ||
        path.join(__dirname, 'data/BHP_POF_DataExport_ME-BHP-2026-001.xlsx');
    const madagascarFile = process.argv[3] || process.env.MADAGASCAR_XLSX ||
        path.join(__dirname, 'data/Adjusted records (12.7 mm base).xlsx');

    console.log("Parsing Chile (POF_Data):", chileFile);
    const chileData = loadAndParse(chileFile, 'POF_Data');

    console.log("Parsing Madagascar (datos):", madagascarFile);
    const madagascarData = loadAndParse(madagascarFile, 'datos');

    const output = [
        {
            id: "chile",
            name: "Minera Escondida - ME-BHP-2026-001 (Cile)",
            data: chileData
        },
        {
            id: "madagascar",
            name: "Madagascar - Adjusted records (12.7 mm base)",
            data: madagascarData
        }
    ];

    const outPath = path.join(__dirname, 'dashboard/public/pipeline_data.json');
    fs.writeFileSync(outPath, JSON.stringify(output, null, 2));

    console.log(`Saved ${output.length} zones to ${outPath}`);
}

run();
