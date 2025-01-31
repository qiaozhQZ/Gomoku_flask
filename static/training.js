$().ready(function(){
    $.ajax({
        type: "GET",
        url: '/training_time_left',
        data: '{}',
        contentType: "application/json",
        dataType: 'json',
        success: function(time_left) {
            debugger;
            console.log(time_left);
            setTimeout(function(){
                $.ajax({
                    type: "POST",
                    url: '/advance_stage',
                    data: JSON.stringify({'page': window.location.pathname.substring(1) }),
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(resp) {
                        window.skipRollback = true;
                        window.location.href = resp['next_page'];
                    },
                });
            }, time_left['seconds']*1000); //wait
        },
    });
});
