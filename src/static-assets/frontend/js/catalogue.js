
$( document ).ready(function() {
    var sort_val = getUrlParameter('sort');
    if (sort_val) {
        $('#sort').val(sort_val).attr("selected", "selected");
        $('#sort-mobile').val(sort_val).attr("selected", "selected");
    }

    var search_val = getUrlParameter('search');
    if (search_val) {
        $('#search').val(search_val);
        $('#search-mobile').val(search_val);
    }

    var init_val = getUrlParameter('initiative');
    if (init_val) {
        console.log(init_val);
        $('#initiative').val(init_val);
    }
});

function getUrlParameter(sParam)
{
    var sPageURL = window.location.search.substring(1);
    var sURLVariables = sPageURL.split('&');
    for (var i = 0; i < sURLVariables.length; i++)
    {
        var sParameterName = sURLVariables[i].split('=');
        if (sParameterName[0] == sParam)
        {
            return sParameterName[1].replace('+', ' ');
        }
    }
}