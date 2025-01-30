$.ajaxSetup({
    type: 'POST',
    timeout: 30000, // set default timeout to 15 sec.
    error: function (request, status, err) {
        if (status == "timeout") {
            // timeout -> reload the page and try again
            console.log("timeout");
        } else {
            // another error occured
            alert("error: " + request + status + err);
        }
        window.location.reload();
    }
})

let xhrPool = [];
let abortController = new AbortController();


$.ajaxSetup({
    beforeSend: function (jqXHR) {
        xhrPool.push(jqXHR);
    },
    complete: function (jqXHR) {
        let index = xhrPool.indexOf(jqXHR);
        if (index > -1) {
            xhrPool.splice(index, 1);
        }
    }
});

$(window).on('beforeunload', function () {
    xhrPool.forEach(function (jqXHR) {
        jqXHR.abort();
    });
    return rollbackTransaction();
});


function rollbackTransaction() {
    return $.ajax({
        url: '/rollback_transaction',
        type: 'POST',
        async: false // Ensure this executes before page unload
    });
}


let clickable = false;
let num_games_left = 99999;

function flip_color() {
    if (move_color == 'black') {
        move_color = 'white';
    } else {
        move_color = 'black';
    }
}

function enable_clicking() {
    clickable = true;
    $('.move_location').addClass('make_clickable');
    $('#hint_button').removeAttr('disabled');
    $('.move_location').click(click_handler);
}

function disable_clicking() {
    clickable = false;
    $('.move_location').removeClass('make_clickable');
    $('#hint_button').attr('disabled', 'disabled');
    $('.move_location').off('click', click_handler);
}

function make_ai_move() {
    showLoader();
    disable_clicking();
    if (move_color == 'white') {
        disable_clicking();
        $.post('get_ai_move').done(function (data) {
            console.log('opponent move:');
            console.log(data);
            $('#loc' + data['location']).removeClass('move_location');
            $('#loc' + data['location']).addClass(move_color + 'stone');
            flip_color();
            $.post('move/' + data['i'] + '/' + data['j'])
                .done(function (data) {
                    $(document).trigger('move_complete', data);
                            console.log('opp move done');
                            console.log(data);
                            enable_clicking();
                            hideLoader();
                            if (data['end']) {
                                display_winner(data['winner']);
                    }

                })
                .error(function (data) {
                    window.location.reload();
                });


        });
    } else {
        enable_clicking();
        hideLoader();
    }

}

function initializeBoard() {
    showLoader();
    disable_clicking();
    $.ajax({
        type: "GET",
        url: '/get_moves',
        contentType: "application/json",
        dataType: 'json',
        success: function (resp) {
            // Clear the board first
            clear_board();

            // Update the board state based on the response
            if (resp.moves && resp.moves.length > 0) {
                resp.moves.forEach(move => {
                    const location = move.location;
                    const color = move.player_move ? 'black' : 'white';
                    $(`#loc${location}`).removeClass('move_location')
                        .addClass(`${color}stone`);
                });
            }

            // Ensure all board elements have data-row and data-col attributes
            $('.move_location').each(function () {
                const location = $(this).attr('id').replace('loc', '');
                const row = Math.floor(location / boardHeight); // Assuming boardHeight is defined
                const col = location % boardWidth; // Assuming boardWidth is defined
                $(this).attr('data-row', row).attr('data-col', col);
            });

            hideLoader();
            enable_clicking(); // Enable clicks only after the board is ready
        },
        error: function (xhr, status, error) {
            hideLoader();
            console.error("Error initializing board:", error);
        }
    });
}

function click_handler(e) {
    if (clickable) {
        showLoader();
        disable_clicking();
        $('.hintstone').removeClass('hintstone');

        let square = this;
        let row = $(square).attr('data-row');
        let col = $(square).attr('data-col');
        disable_clicking();

        $('#score').html('--');
        $(square).off('click')
        $(square).removeClass('move_location');
        $(square).addClass(move_color + 'stone');


        flip_color();

        $.post('move/' + row + '/' + col)
            .done(function (data) {
                $(document).trigger('move_complete', data);
                console.log('your move:');
                console.log(data);
                $('#score').html(data['score']);

                if (data['end']) {
                    display_winner(data['winner']);
                } else {
                    make_ai_move();
                }
            })
            .error(function (data) {
                window.location.reload();
            });
    }
}

function display_winner(winner) {
    $(document).trigger('game_end');
    disable_clicking();
    $('#toolbar').hide();
    $('#start_instructions').hide();
    $('#winning_dialog').show();
    if (winner == 1) {
        $('#winning_text').text('You Won!');
    } else if (winner == 2) {
        $('#winning_text').text('You Lost!');
    } else {
        $('#winning_text').text('Draw Game!');
    }
    num_games_left -= 1; //count down the games left

    if (num_games_left < 1) { //advance to survey if no games left
        $.ajax({
            type: "POST",
            url: '/advance_stage',
            data: JSON.stringify({'page': 'testing'}),
            contentType: "application/json",
            dataType: 'json',
            success: function (resp) {
                $('#new_game_button').hide();
                $('#next_button').click(function () {
                    window.location.href = resp['next_page'];
                });
                $('#next_button').show();
            },
        });
    }
}

function clear_board() {
    $('.blackstone').addClass('move_location').addClass('make_clickable').removeClass('blackstone');
    $('.whitestone').addClass('move_location').addClass('make_clickable').removeClass('whitestone');
    $('.hintstone').removeClass('hintstone');
    move_color = "black";
}


// Function to show the loader
function showLoader() {
    disable_clicking();
    document.getElementById('ai-loader').style.display = 'block';
}

// Function to hide the loader
function hideLoader() {
    document.getElementById('ai-loader').style.display = 'none';
}

function isMovesOdd() {
    // Get all stones currently on the board
    const blackStones = $('.blackstone').length;
    const whiteStones = $('.whitestone').length;
    const totalMoves = blackStones + whiteStones;

    // Check if total moves is odd
    return totalMoves % 2 === 1;
}

$().ready(function () {
    showLoader();
    disable_clicking();
    var is_move_odd = false;
    $.ajax({
        type: "GET",
        url: '/get_moves',
        contentType: "application/json",
        dataType: 'json',
        success: function (resp) {
            if (resp['moves'] % 2 == 1) {
                is_move_odd = true;
            }
        },
    });
    if (isMovesOdd() || is_move_odd) {
        disable_clicking();
        showLoader();
        make_ai_move();

    } else {
        hideLoader();
        enable_clicking();
    }
    window.addEventListener("pageshow", function (event) {
        var historyTraversal = event.persisted ||
            (typeof window.performance != "undefined" &&
                window.performance.getEntriesByType("navigation")[0].type === "back_forward"
            );
        if (historyTraversal) {
            // Handle page restore.
            window.location.reload();
        }
    });

    // $('#next_button').hide();

    $('#hint_button').click(function (e) {
        if (clickable) {
            disable_clicking();
            $('.hintstone').removeClass('hintstone');
            $.post('get_hint').done(function (data) {
                $('#loc' + data['location']).addClass('hintstone');
                enable_clicking();
                $.ajax({
                    type: "POST",
                    url: '/log',
                    data: JSON.stringify({'event': 'hint', 'location': data['location']}),
                    contentType: "application/json",
                    dataType: 'json',
                    success: function (resp) {
                    },
                });
            });
        }
    });

    $('#new_game_button').click(function () {
        clear_board();
        hideLoader();
        // Abort any ongoing requests
        abortController.abort();
        abortController = new AbortController();

        // End the previous game
        fetch('/end_game', {
            method: 'POST',
            signal: abortController.signal,
        }).then(response => {
            if (!response.ok) {
                console.error("Failed to end previous game");
            }
        }).catch(error => {
            if (error.name !== 'AbortError') {
                console.error("Error ending previous game:", error);
            }
        });
        // Roll back any incomplete transactions
        fetch('/rollback_transaction', {
            method: 'POST',
            signal: abortController.signal,
        }).then(response => {
            if (!response.ok) {
                console.error("Rollback failed");
            }
        }).catch(error => {
            if (error.name !== 'AbortError') {
                console.error("Rollback error:", error);
            }
        });
        clear_board();
        // initializeBoard();
        move_color = 'black';
        $.ajax({
            type: "POST",
            url: '/new_game',
            data: JSON.stringify({}),
            contentType: "application/json",
            dataType: 'json',
            success: function (resp) {
                $(document).trigger('new_game');
                clear_board();
                $('#toolbar').show();
                $('#winning_dialog').hide();
                $('#start_instructions').show();
                hideLoader();
                enable_clicking();
                $('#score').html('--');
            },
        });

        $.ajax({
            type: "POST",
            url: '/log',
            data: JSON.stringify({'event': 'new_game'}),
            contentType: "application/json",
            dataType: 'json',
            success: function (resp) {
            },
        });
    });


});
