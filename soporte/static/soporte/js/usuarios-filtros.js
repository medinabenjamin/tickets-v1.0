(function() {
    const form = document.getElementById('filters-form');
    const searchInput = document.getElementById('searchInput');
    if (!form || !searchInput) return;

    const submitWithParams = () => {
        const params = new URLSearchParams(new FormData(form));
        params.set('page', '1');
        const url = `${window.location.pathname}?${params.toString()}`;
        window.location = url;
    };

    let debounceTimer = null;
    searchInput.addEventListener('input', () => {
        if (debounceTimer) {
            clearTimeout(debounceTimer);
        }
        debounceTimer = setTimeout(submitWithParams, 300);
    });

    ['roleSelect', 'estadoSelect'].forEach(id => {
        const field = document.getElementById(id);
        if (field) {
            field.addEventListener('change', submitWithParams);
        }
    });
})();
