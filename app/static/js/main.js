document.addEventListener('DOMContentLoaded', function() {
    // --- Search A: Dropdowns ---
    const searchAOrder = ['vehicle_type', 'make', 'model', 'engine', 'ecu_type'];
    const searchAParent = {
        'make': 'vehicle_type',
        'model': 'make',
        'engine': 'model',
        'ecu_type': 'engine'
    };

    function populateSelect(field, parentField = null, parentValue = null) {
        const select = document.getElementById(field);
        if (!select) {
            // Element doesn't exist on this page, skip
            return;
        }
        
        let url = `/api/dropdown/${field}`;
        if (parentField && parentValue) {
            url += `?parent_field=${parentField}&parent_value=${encodeURIComponent(parentValue)}`;
        }
        fetch(url)
            .then(response => response.json())
            .then(data => {
                select.innerHTML = '<option value="">-- Select --</option>';
                if (data.values) {
                    data.values.forEach(val => {
                        select.innerHTML += `<option value="${val}">${val}</option>`;
                    });
                }
                clearChildSelects(field);
            })
            .catch(error => {
                console.error('Error fetching dropdown data:', error);
            });
    }

    function clearChildSelects(field) {
        const idx = searchAOrder.indexOf(field);
        for (let i = idx + 1; i < searchAOrder.length; i++) {
            const select = document.getElementById(searchAOrder[i]);
            if (select) select.innerHTML = '<option value="">-- Select --</option>';
        }
    }

    // Only initialize dropdowns if vehicle_type element exists (indicating this page has dropdowns)
    const vehicleTypeSelect = document.getElementById('vehicle_type');
    if (vehicleTypeSelect) {
        // Initial population for Search A
        populateSelect('vehicle_type');
        
        searchAOrder.forEach(function(field, idx) {
            const select = document.getElementById(field);
            if (!select) return;
            select.addEventListener('change', function() {
                // Only populate the next field in the chain
                if (idx < searchAOrder.length - 1) {
                    const childField = searchAOrder[idx + 1];
                    populateSelect(childField, field, select.value);
                }
                // Do NOT repopulate the current select!
            });
        });
    }
});
