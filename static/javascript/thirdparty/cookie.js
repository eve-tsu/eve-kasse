/** Cookie handling for Prototype. */

var Cookie = {

	get: function(key) {
		val = document.cookie.split(';').find(function(elem, index) {
			if (elem.trim().match('^'+key)) {
				return true;
			} else {
				return false;
			}
		});
		if (typeof(val) !== 'undefined' && val != null) {
			return val.substr(key.length+1).trim();
		}
		if (arguments.length == 2) {
			return arguments[1];
		}
		return
	}

};
