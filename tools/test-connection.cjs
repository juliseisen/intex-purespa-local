#!/usr/bin/env node
/*
 * Verbindungstest für Tuya-basierte Intex PureSpa (TY-Modelle).
 *
 * Aufruf: node test-connection.cjs <IP> <DEVICE_ID> <LOCAL_KEY> [VERSION]
 *
 * Probiert ohne VERSION alle Protokollversionen (3.3, 3.4, 3.5, 3.1)
 * durch und gibt die empfangenen Datenpunkte (dps) aus.
 *
 * Benötigt: npm install tuyapi
 */

const TuyAPI = require("tuyapi");

const [, , ip, id, key, versionArg] = process.argv;

if (!ip || !id || !key) {
  console.error(
    "Aufruf: node test-connection.cjs <IP> <DEVICE_ID> <LOCAL_KEY> [VERSION]"
  );
  process.exit(2);
}

const versions = versionArg ? [versionArg] : ["3.3", "3.4", "3.5", "3.1"];

function tryVersion(version) {
  return new Promise((resolve, reject) => {
    const device = new TuyAPI({
      id,
      key,
      ip,
      version,
      issueGetOnConnect: false,
    });

    const timer = setTimeout(() => {
      device.disconnect();
      reject(new Error("Timeout (10s)"));
    }, 10000);

    device.on("error", (err) => {
      clearTimeout(timer);
      device.disconnect();
      reject(err);
    });

    device
      .connect()
      .then(() => device.get({ schema: true }))
      .then((status) => {
        clearTimeout(timer);
        device.disconnect();
        resolve(status);
      })
      .catch((err) => {
        clearTimeout(timer);
        device.disconnect();
        reject(err);
      });
  });
}

(async () => {
  for (const version of versions) {
    process.stdout.write(`Protokoll ${version} ... `);
    try {
      const status = await tryVersion(version);
      console.log("ERFOLG!\n");
      console.log("Antwort des Spa:");
      console.log(JSON.stringify(status, null, 2));
      console.log(
        `\n==> Funktionierende Protokollversion: ${version}\n` +
          "Bekannte Datenpunkte: 103=Sanitizer 104=Power 105=Jets " +
          "106=Filter 107=Bubbles 108=Heizung 109=Solltemp 110=Isttemp 114=Restzeit"
      );
      process.exit(0);
    } catch (err) {
      console.log(`fehlgeschlagen (${err.message})`);
    }
  }
  console.error(
    "\nKeine Protokollversion hat funktioniert. Mögliche Ursachen:\n" +
      "- Local Key falsch oder veraltet (ändert sich beim Neu-Anlernen!)\n" +
      "- Device ID falsch\n" +
      "- Ein anderes Programm (LocalTuya?) belegt die einzige lokale Verbindung"
  );
  process.exit(1);
})();
