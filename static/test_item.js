let test_item = null;
let time = 0;

function load_problem(resp){
    if (typeof resp === 'object' && Object.keys(resp).length === 0){
        console.log("DONE!");
        console.log(window.location.pathname)
        $.ajax({
            type: "POST",
            url: '/advance_stage',
            data: JSON.stringify({'page': window.location.pathname.substring(1) }),
            contentType: 'application/json',
            dataType: 'json',
            success: function(resp) {
                window.location.href = resp['next_page'];
            },
        });
    }

    test_item = resp['item_id']

    // prob info
    $('#total_probs').html(resp['total_probs']);
    $('#completed_probs').html(resp['completed_probs']);

    // set timer
    time = parseInt(resp['seconds']);
    $('#timer').html(time);
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
                }
            });
        }
    }, 1000);

    // initialize board
    $('.move_location').removeClass('whitestone')
    $('.move_location').removeClass('blackstone')

    resp['moves'].forEach(function(move){
        let selector = '.move_location[data-row="' + move['y'] + '"][data-col="' + move['x'] + '"]';
        let elements = $(selector).addClass(move['color'] + "stone");
    });

    // bind event listeners for making move
    $('.move_location').click(function(data){
        let ele = $(data.currentTarget);
        let x = ele.data('col');
        let y = ele.data('row');

        $.ajax({
            type: "POST",
            url: '/answer_test_item',
            data: JSON.stringify({"test_item_id": test_item, "move": {'x': x,
                'y': y, 'color': 'black'}}),
            contentType: 'application/json',
            dataType: 'json',
            success: function(resp) {
                load_problem(resp);
            }
        });

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
        }
    });

}

$().ready(function(){
    get_problem();
});
