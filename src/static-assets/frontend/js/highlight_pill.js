
$( document ).ready(function() {
    let page_id = getEndofURL();
    let selector = '.pill-' + page_id.toString()

    // set .all-pills to blue
    $('.all-pills').addClass('blue-pill')

    // then set the classes
    $(selector).removeClass('blue-pill')
    $(selector).addClass('white' + '-pill')

});

function getEndofURL()
{
    let split_url = location.pathname.split('/');
    return split_url[split_url.length - 1]
}