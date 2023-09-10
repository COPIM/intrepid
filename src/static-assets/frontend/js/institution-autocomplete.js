
function activate_autocomplete(url) {
    function log(message) {
        $("<div>").text(message).prependTo("#inst_lookup");
        $("#inst_lookup").scrollTop(0);
    }

    $("#inst_lookup").autocomplete({
        source: function (request, response) {
            $.ajax({
                url: url,
                dataType: "jsonp",
                data: {
                    term: request.term
                },
                success: function (data) {
                    response(data);
                }
            });
        },
        minLength: 2,
        select: function (event, ui) {
            $('#institution_ROR').val(ui.item.id);
        }
    });
}
