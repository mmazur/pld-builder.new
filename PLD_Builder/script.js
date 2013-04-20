
// update date stamps to reflect viewers timezone
function update_tz(t) {
	var el, off, dt,
		collection = document.getElementsByTagName('span');
	for (off in collection) {
		el = collection[off];
		if (el.id == 'tz') {
			dt = new Date(el.innerHTML).toString();
			// strip timezone name, it is usually wrong when not initialized
			// from TZ env, but reverse calculated from os data
			dt = dt.replace(/\s+\(.+\)/, "");
			// strip "GMT"
			dt = dt.replace(/GMT/, "");
			el.innerHTML = dt;
		}
	}
}

window.onload = update_tz;
