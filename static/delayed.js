function disable_review() {
    console.log('disable?');
    $('#new_game_button').hide();
    $('#end_game_button').show();
    $('#review').hide();
    $('#end_game_button').show();
    $('#start_instructions').show();
}

function enable_review() {
    $('#new_game_button').show();
    $('#end_game_button').hide();
    $('#end_game_button').hide();
    $('#review').show();
    $('#start_instructions').hide();
    $('.move_location').removeClass('make_clickable');
    $('.move_location').off('click', click_handler);
    hide_loader();

    if (current_idx % 2 == 0) {
        $('#score').html(score_seq[current_idx]);
        $('#loc' + move_seq[current_idx]).addClass("newstone");
        $('#hint').prop("disabled", false);
    } else {
        $('#score').html('--');
        $('#hint').prop("disabled", true);
    }

}

$().ready(function(){

    disable_review();

    function prev_move() {
        if (current_idx >= 0) {
            $('.hintstone').removeClass('hintstone');
            $('#loc' + move_seq[current_idx]).removeClass(color_seq[current_idx] + "stone");
            current_idx -= 1;

            if (current_idx >= 0 && current_idx % 2 == 0) {
                $('#score').html(score_seq[current_idx]);
                $('#hint').prop("disabled", false);
            } else {
                $('#score').html('--');
                $('#hint').prop("disabled", true);
            }
        }
    }

    function next_move() {
        if (current_idx < move_seq.length - 1) {
            $('.hintstone').removeClass('hintstone');
            current_idx += 1;
            $('#loc' + move_seq[current_idx]).addClass(color_seq[current_idx] + "stone");

            if (current_idx >= 0 && current_idx % 2 == 0) {
                $('#score').html(score_seq[current_idx]);
                $('#hint').prop("disabled", false);
            } else {
                $('#score').html('--');
                $('#hint').prop("disabled", true);
            }
        }
    }

    $('#previous').click(function () {
        $('.newstone').removeClass('newstone');
        prev_move();

        if (current_idx % 2 == 1) {
            prev_move();
        }

        $('#loc' + move_seq[current_idx]).addClass("newstone");

        $.ajax({
            type: "POST",
            url: '/log',
            data: JSON.stringify({'event': 'previous'}),
            contentType: "application/json",
            dataType: 'json',
            success: function (resp) {
            },
        });
    });

    $('#next').click(function () {
        $('.newstone').removeClass('newstone');
        next_move();

        if (current_idx % 2 == 1) {
            next_move();
        }

        if (current_idx % 2 == 0) {
            $('#loc' + move_seq[current_idx]).addClass("newstone");
        }

        $.ajax({
            type: "POST",
            url: '/log',
            data: JSON.stringify({'event': 'next'}),
            contentType: "application/json",
            dataType: 'json',
            success: function (resp) {
            },
        });
    });

    $('#first').click(function () {
        $('.newstone').removeClass('newstone');
        while (current_idx >= 0) {
            prev_move();
        }
        $.ajax({
            type: "POST",
            url: '/log',
            data: JSON.stringify({'event': 'first'}),
            contentType: "application/json",
            dataType: 'json',
            success: function (resp) {
            },
        });
        ('#loc' + move_seq[current_idx]).addClass("newstone");
    });

    $('#last').click(function () {
        $('.newstone').removeClass('newstone');
        while (current_idx < move_seq.length - 1) {
            next_move();
        }
        $.ajax({
            type: "POST",
            url: '/log',
            data: JSON.stringify({'event': 'last'}),
            contentType: "application/json",
            dataType: 'json',
            success: function (resp) {
            },
        });
        ('#loc' + move_seq[current_idx]).addClass("newstone");
    });

    $('#hint').click(function () {
        if (current_idx % 2 == 0) {
            $('.hintstone').removeClass('hintstone');
            $('#loc' + hint_seq[current_idx]).addClass('hintstone');
            $.ajax({
                type: "POST",
                url: '/log',
                data: JSON.stringify({'event': 'hint', 'location': hint_seq[current_idx + 1]}),
                contentType: "application/json",
                dataType: 'json',
                success: function (resp) {
                },
            });
        }
    });

    $('#end_game_button').click(function () {
        disable_clicking();
        $(document).trigger('game_end');
    });

    $(document).on("new_game", function () {
        disable_review();
        move_seq = [];
        color_seq = [];
        score_seq = [];
        hint_seq = [];
        current_idx = -1;
    });

    window.activeAIRequest = null;
    $(document).on("game_end", function() {
        if (window.activeAIRequest) {
            window.activeAIRequest.abort();
        }
        $.ajax({
            type: "POST",
            url: '/new_game',
            data: JSON.stringify({}),
            contentType: "application/json",
            dataType: 'json',
            success: function(resp) {
                enable_review();
            },
        });

        $.ajax({
            type: "POST",
            url: '/log',
            data: JSON.stringify({'event':'end_game'}),
            contentType: "application/json",
            dataType: 'json',
            success: function(resp) {},
        });
    });

    $(document).on("move_complete", function(ev, data){
        move_seq.push(data['move']);
        color_seq.push(data['color']);
        score_seq.push(data['score']);
        hint_seq.push(data['hint']);
        current_idx += 1;
    });

});
