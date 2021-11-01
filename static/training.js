$().ready(function(){
	$.ajax({
		type: "GET",
		url: '/training_time_left',
		data: '{}',
		contentType: "application/json",
		dataType: 'json',
		success: function(time_left) {
			console.log(time_left);
			setTimeout(function(){ 
				$.ajax({
					type: "POST",
					url: '/advance_stage',
					data: JSON.stringify({'page':'training'}),
					contentType: 'application/json',
					dataType: 'json',
					success: function() {
						window.location.href = "/testing";
					},
				});
			}, time_left['seconds']*1000); //wait
		},
	});
});
