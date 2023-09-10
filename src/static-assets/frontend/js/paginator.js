function update(a, b) {
    // sets a querystring building on whatever is already in ths search bar
    let searchParams = new URLSearchParams(window.location.search);
    if (b !== '')
        searchParams.set(a, b);
    else
        searchParams.delete(a);
    window.location.search = searchParams.toString();
}
