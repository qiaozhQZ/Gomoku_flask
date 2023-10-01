let test_item = null;
let time = -1;

function load_problem(resp){
    if (typeof resp === 'object' && Object.keys(resp).length === 0){
        console.log("DONE!");
        console.log(window.location.pathname)
        $.ajax({
            type: "POST",
            url: '/advance_stage',
            timeout: 30000, // set to 30 sec or 30000 millisec
            data: JSON.stringify({'page': window.location.pathname.substring(1) }),
            contentType: 'application/json',
            dataType: 'json',
            success: function(resp) {
                window.location.href = resp['next_page'];
            },
            error: function(request, status, err) {
                if (status == "timeout") {
                    // timeout -> reload the page and try again
                    console.log("timeout");
                    window.location.reload();
                } else {
                    // another error occured
                    alert("error: " + request + status + err);
                }
            }
        });
    }

    test_item = resp['item_id']

    // prob info
    $('#total_probs').html(resp['total_probs']);
    $('#completed_probs').html(resp['completed_probs']);

    // set timer
    time = parseInt(resp['seconds']);
    $('#timer').html(time);

    // initialize board
    $('.move_location').removeClass('whitestone')
    $('.move_location').removeClass('blackstone')

    // bind event listeners for making move
    $('.move_location').unbind('click');
    $('.move_location').click(function(data){
        let ele = $(data.currentTarget);
        let x = ele.data('col');
        let y = ele.data('row');

        $.ajax({
            type: "POST",
            url: '/answer_test_item',
            timeout: 30000, // set to 30 sec or 30000 millisec
            data: JSON.stringify({"test_item_id": test_item, "move": {'x': x,
                'y': y, 'color': 'black'}}),
            contentType: 'application/json',
            dataType: 'json',
            success: function(resp) {
                load_problem(resp);
            },
            error: function(request, status, err) {
                if (status == "timeout") {
                    // timeout -> reload the page and try again
                    console.log("timeout");
                    window.location.reload();
                } else {
                    // another error occured
                    alert("error: " + request + status + err);
                }
            }
        });

    });

    resp['moves'].forEach(function(move){
        let selector = '.move_location[data-row="' + move['y'] + '"][data-col="' + move['x'] + '"]';
        $(selector).addClass(move['color'] + "stone");
        $(selector).unbind('click');
    });

}

function get_problem(){
    $.ajax({
        type: "POST",
        url: '/current_test_item_info',
        data: '{}', //should be empty here
        contentType: 'application/json',
        dataType: 'json',
        success: function(resp) {
            load_problem(resp);
        },
        timeout: 30000, // set to 30 sec or 30000 millisec
        error: function(request, status, err) {
            if (status == "timeout") {
                // timeout -> reload the page and try again
                console.log("timeout");
                window.location.reload();
            } else {
                // another error occured
                alert("error: " + request + status + err);
            }
        }
    });

}

$().ready(function(){
    setInterval(function () {
        time -= 1;
        if (time > 0) {
            $('#timer').html(time);
        } else {
            if (time == 0){
                $('#timer').html(time);
            }
            $.ajax({
                type: "POST",
                url: '/answer_test_item',
                data: JSON.stringify({"test_item_id": test_item, "move": "timeout"}),
                contentType: 'application/json',
                dataType: 'json',
                success: function(resp) {
                    load_problem(resp);
                },
                timeout: 30000, // set to 30 sec or 30000 millisec
                error: function(request, status, err) {
                    if (status == "timeout") {
                        // timeout -> reload the page and try again
                        console.log("timeout");
                        window.location.reload();
                    } else {
                        // another error occured
                        alert("error: " + request + status + err);
                    }
                }
            });
        }
    }, 1000);

    get_problem();

});
