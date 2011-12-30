/*
 * @author	W-Mark Kubacki; kubacki@hurrikane.de
 * Replace that author ^^
 */

function display_error(msg) {
	if(window['Modalbox']) {
		// some nice way to show messages
		Modalbox.MessageBox.alert("Error Frenzy!", msg);
	} else {
		// the ECMA-script way to show messages
		alert(msg);
	}
	// Want logging? put it in here!
}

/* AJAJ or AJAX */
function obtJSON(method, url, postVars, onCompleteCallback) {
	new Ajax.Request(url, {
		method: method,
		parameters: postVars,
		requestHeaders: ['Content-Type', 'application/x-www-form-urlencoded'],
		onSuccess: function(r) {
			var json = r.responseText.evalJSON();
			onCompleteCallback(json);
		},
		onFailure: function(r) {
			var json = r.responseText.evalJSON();
			if(json['error']) {
				display_error(json['error']);
			} else {
				display_error('An undefined error occured. Please see the logs.');
			}
		}
	});
}
function postJSON(url, postVars, onCompleteCallback) {
	return obtJSON('post', url, Object.extend(postVars, {'_xsrf': Cookie.get('_xsrf')}), onCompleteCallback);
}
function getJSON(url, postVars, onCompleteCallback) {
	return obtJSON('get', url, postVars, onCompleteCallback);
}

/* Spinner spins spinning spins. */
Ajax.Responders.register({
	onCreate: function() {
		$('global_spinner').show();
	},
	onComplete: function() {
		if(Ajax.activeRequestCount <= 0) {
			$('global_spinner').hide();
		}
	}
});

document.observe('dom:loaded', function() {
	var spinner = $('global_spinner');
	if(spinner) { spinner.hide(); }
});

/* Your application-specific JS goes here. */
var Something = {
	someMethod: function() {
		function localCallback(result) {
			// do something with result (which is in JSON)
		}
		// will use site.dns_cname if set
		postJSON('/someController', {}, localCallback);
	}
}
