$(document).ready(function () {

    $('.max-stat-check').on('change', function () {
        if (this.checked) {
            $('.max-stat-check').not(this).prop('checked', false);
        }
    });

    // Show/hide realm input depending on selected mode
    $('input[name="scan_mode"]').on('change', function () {
        const mode = $('input[name="scan_mode"]:checked').val();
        $('#single-realm-input').toggle(mode === 'single');
    });

    // === Stat mode toggle ===
    $('#statModeSwitch').on('change', function () {
        const isAdvanced = $(this).is(':checked');
        $('#statModeLabel').text(`Mode: ${isAdvanced ? 'Advanced' : 'Normal'}`);
        $('#stat-normal-mode').toggle(!isAdvanced);
        $('#stat-advanced-mode').toggle(isAdvanced);
    });

    // Toggle logic for 'stat-check' checkboxes (max 2 selected)
    $('.stat-check').on('change', function () {
        const checked = $('.stat-check:checked');
        if (checked.length > 2) {
            this.checked = false;
            alert('You can select up to 2 stats.');
            return;
        }

        // If none selected, enable 'All Stats'
        if (checked.length === 0 && $('.max-stat-check:checked').length === 0) {
            $('#all-stats').prop('checked', true);
            $('.stat-check, .max-stat-check').prop('disabled', true);
        } else {
            $('#all-stats').prop('checked', false);
            $('.stat-check, .max-stat-check').prop('disabled', false);
        }
    });

    // Only 1 Max-{Stat} checkbox allowed
    $('.max-stat-check').on('change', function () {
        if (this.checked) {
            $('.max-stat-check').not(this).prop('checked', false);
        }

        // If all other filters cleared, enable 'All Stats'
        if (
            $('.stat-check:checked').length === 0 &&
            $('.max-stat-check:checked').length === 0
        ) {
            $('#all-stats').prop('checked', true);
            $('.stat-check, .max-stat-check').prop('disabled', true);
        } else {
            $('#all-stats').prop('checked', false);
            $('.stat-check, .max-stat-check').prop('disabled', false);
        }
    });

    // Toggle: All Stats checkbox
    $('#all-stats').on('change', function () {
        const isAll = $(this).is(':checked');
        $('.stat-check, .max-stat-check').prop('disabled', isAll);
        if (isAll) {
            $('.stat-check, .max-stat-check').prop('checked', false);
        }
    });

    $('#gearTable').DataTable({
        columnDefs: [
            { targets: 7, type: "num" },
            { targets: 8, type: "num" }
        ],
        order: [],
        autoWidth: false
    });

    let activeSlots = new Set();
    let activeArmorTypes = new Set();

    $('.slot-button').click(function () {
        const slot = $(this).data('slot');
        const type = $(this).data('type');

        $(this).toggleClass('active');

        if (slot) {
            if (activeSlots.has(slot)) {
                activeSlots.delete(slot);
            } else {
                activeSlots.add(slot);
            }
        }

        if (type) {
            if (activeArmorTypes.has(type)) {
                activeArmorTypes.delete(type);
            } else {
                activeArmorTypes.add(type);
            }
        }
    });

    // === Fully Updated $('#scanForm').on('submit') Function ===
    $('#scanForm').on('submit', function (e) {
        e.preventDefault();
        $('#scanStatus').html('');
        $('#scanProgress').removeClass('d-none');
        $('#scanProgressBar')
            .removeClass('bg-danger bg-success')
            .addClass('progress-bar-animated')
            .text('Scanning...');

        const selectedSlots = Array.from(activeSlots);
        const selectedArmorTypes = Array.from(activeArmorTypes);

        const config = {
            MIN_ILVL: parseInt($('input[name="min_ilvl"]').val()) || 0,
            MAX_ILVL: parseInt($('input[name="max_ilvl"]').val()) || 1000,
            MAX_BUYOUT: (parseInt($('input[name="max_buyout"]').val()) || 10000000) * 10000,

            ALLOWED_ARMOR_SLOTS: selectedSlots.filter(s => [
                "Head", "Shoulder", "Chest", "Waist", "Legs", "Feet", "Back", "Wrist", "Hands"
            ].includes(s)),

            ALLOWED_WEAPON_SLOTS: selectedSlots.filter(s => [
                "One-Hand", "Two-Hand", "Main-Hand", "Off-Hand", "Held In Off-hand", "Ranged", "Ranged Right"
            ].includes(s)),

            ALLOWED_ACCESSORY_SLOTS: selectedSlots.filter(s => [
                "Finger", "Trinket", "Neck", "Held In Off-hand"
            ].includes(s)),

            ALLOWED_ARMOR_TYPES: selectedArmorTypes,
            ALLOWED_WEAPON_TYPES: presets.full.weapon_types,

            FILTER_TYPE: [],
            STAT_DISTRIBUTION_THRESHOLDS: {
                Haste: 0,
                Crit: 0,
                Vers: 0,
                Mastery: 0,
                Speed: 0
            }
        };

        config.slots = selectedSlots;


        // === Scan Mode Handling ===
        const scan_mode = $('input[name="scan_mode"]:checked').val();
        if (scan_mode === "single") {
            config.scan_mode = "single";
            config.realm = $('#realm_input').val().trim();
        } else {
            config.scan_mode = "all";
        }

        // === Stat Mode Handling ===
        const isAdvanced = $('#statModeSwitch').is(':checked');
        if (isAdvanced) {
            config.STAT_DISTRIBUTION_THRESHOLDS = {
                Haste: parseInt($('#haste-val').val()) || 0,
                Crit: parseInt($('#crit-val').val()) || 0,
                Vers: parseInt($('#vers-val').val()) || 0,
                Mastery: parseInt($('#mastery-val').val()) || 0,
                Speed: $('#speed').is(':checked') ? 71 : 0
            };
        } else {
            const selectedStats = $('.stat-check:checked').map((_, el) => el.value).get();
            const selectedMax = $('.max-stat-check:checked').map((_, el) => el.value).get();

            const otherFilters = [];
            if ($('#speed').is(':checked')) otherFilters.push("Speed");
            if ($('#prismatic').is(':checked')) otherFilters.push("Prismatic");

            const combined = [...selectedStats, ...selectedMax, ...otherFilters];

            if (!$('#all-stats').is(':checked') && combined.length > 0) {
                config.FILTER_TYPE = combined;
            }
        }

        // === Update Scan Preview UI ===
        $('#scanDetails').html(`<code>Running scan with:</code><br>
            <strong>Item Level:</strong> ${config.MIN_ILVL}–${config.MAX_ILVL}<br>
            <strong>Max Buyout:</strong> ${config.MAX_BUYOUT}g<br>
            <strong>Filters:</strong> ${config.FILTER_TYPE?.join(", ") || "All"}`);

        // === AJAX POST to Flask backend ===
        $.ajax({
            type: 'POST',
            url: '/scan',
            contentType: 'application/json',
            data: JSON.stringify(config),
            success: function (response) {
                if (response.success) {
                    if (response.no_results) {
                        $('#scanProgressBar')
                            .removeClass('bg-success bg-danger')
                            .addClass('bg-warning')
                            .removeClass('progress-bar-animated')
                            .text('⚠️ No results found');

                        $('#scanStatus').html('<span class="text-warning">⚠️ Scan completed but no results matched filters.</span>');

                        $('#gearTable').DataTable().clear().draw(); // Optional: clear old table
                    } else {
                        $('#scanProgressBar')
                            .removeClass('bg-danger')
                            .addClass('bg-success')
                            .removeClass('progress-bar-animated')
                            .text('✅ Scan complete');

                        $('#scanStatus').html('<span class="text-success">✅ Scan completed with new results.</span>');

                        setTimeout(() => {
                            $('#scanProgress').addClass('d-none');
                            reloadTable(true);
                        }, 1000);
                    }
                }

            },
            error: function () {
                $('#scanProgressBar')
                    .removeClass('bg-success')
                    .addClass('bg-danger')
                    .removeClass('progress-bar-animated')
                    .text('❌ AJAX error');
            }
        });

        console.log("📤 Submitting scan config:", config);
    });



    // === Reloads table from backend data ===
    function reloadTable(force = false) {
        $.get('/reload', function (data) {
            const table = $('#gearTable').DataTable();
            table.clear();

            for (let row of data) {
                const ilvl = parseInt(row.ilvl) || 0;
                const gold = parseInt(row.buyout_gold) || 0;

                // === Format cell contents
                const stat1 = row.stat1 || "—";
                const stat2 = row.stat2 || "—";
                const itemType = row.type || "—";
                const slot = row.slot || "—";
                const name = row.name || "—";
                const realm = row.realm || "—";
                const item_id = row.item_id || "—";

                const ilvlCell = `<span class="stat-ilvl" data-sort="${ilvl}">${ilvl}</span>`;
                const goldCell = `<span class="stat-buyout" data-sort="${gold}">${gold.toLocaleString()}g</span>`;

                table.row.add([
                    realm,
                    item_id,
                    itemType,
                    slot,
                    stat1,
                    stat2,
                    name,
                    ilvlCell,
                    goldCell
                ]);
            }

            table.draw();

            // Optional: visually confirm refresh if triggered manually
            if (force) {
                $('#scanStatus').html('<span class="text-success">✅ Data refreshed</span>');
            }
        });
    }


    function applyPreset(presetName) {
        const preset = presets[presetName];
        if (!preset) return;

        // === Reset filters
        $("#scanForm input[type='checkbox']").prop("checked", false);
        $('.slot-button').removeClass('active');
        activeSlots.clear();
        activeArmorTypes.clear();

        // === Apply all 10 stat-related checkboxes
        const allStatKeys = [
            "haste", "crit", "vers", "mastery",
            "max-haste", "max-crit", "max-vers", "max-mastery",
            "speed", "prismatic"
        ];
        for (let key of allStatKeys) {
            if (preset[key]) {
                $(`#${key}`).prop("checked", true);
            }
        }

        // === Apply numeric fields
        $("input[name='min_ilvl']").val(preset.min_ilvl || "");
        $("input[name='max_ilvl']").val(preset.max_ilvl || "");
        $("input[name='max_buyout']").val(preset.max_buyout || "");

        // === Apply slot buttons
        for (let slot of preset.slots || []) {
            const btn = $(`.slot-button[data-slot='${slot}']`);
            if (btn.length) {
                btn.addClass("active");
                activeSlots.add(slot);
            }
        }

        // === Apply armor types
        for (let type of preset.armor_types || []) {
            const btn = $(`.slot-button[data-type='${type}']`);
            if (btn.length) {
                btn.addClass("active");
                activeArmorTypes.add(type);
            }
        }
    }


    $('.btn-preset').click(function () {
        $('.btn-preset').removeClass('active');
        $(this).addClass('active');
        const presetName = $(this).data('preset');
        applyPreset(presetName);
    });

    // Initial table load
    reloadTable(false); // Do not show message on initial page load

});

const presets = {
    full: {
        haste: false,
        crit: false,
        vers: false,
        mastery: false,
        "max-haste": false,
        "max-crit": false,
        "max-vers": false,
        "max-mastery": false,
        speed: true,
        prismatic: true,
        min_ilvl: 1,
        max_ilvl: 1000,
        max_buyout: 10000000,
        slots: [
            "Head", "Chest", "Shoulder", "Waist", "Legs", "Wrist", "Hands", "Back", "Feet",
            "One-Hand", "Two-Hand", "Main-Hand", "Held In Off-hand", "Off-Hand", "Off Hand", "Ranged", "Ranged Right",
            "Finger", "Trinket", "Held In Off-hand", "Neck"
        ],
        armor_types: ["Cloth", "Leather", "Mail", "Plate", "Miscellaneous"],
        weapon_types: [
            "Dagger", "Sword", "Axe", "Mace", "Fist Weapon", "Polearm", "Staff", "Off-Hand",
            "Warglaives", "Gun", "Bow", "Crossbow", "Thrown", "Shield", "Wand", "Off Hand", "Ranged Right"
        ]
    },

    custom: {
        haste: true,
        crit: false,
        vers: false,
        mastery: false,
        "max-haste": true,
        "max-crit": false,
        "max-vers": false,
        "max-mastery": false,
        speed: true,
        prismatic: true,
        min_ilvl: 320,
        max_ilvl: 357,
        max_buyout: 10000000,
        slots: [
            "Waist", "Legs", "Wrist", "Hands", "Back", "Feet",
            "One-Hand", "Two-Hand", "Main-Hand", "Off-Hand",
            "Finger", "Trinket", "Held In Off-hand"
        ],
        armor_types: ["Cloth", "Leather", "Miscellaneous"],
        weapon_types: ["Dagger", "Mace", "Fist Weapon", "Polearm", "Staff", "Off Hand"]
    },

    profitable: {
        haste: false,
        crit: false,
        vers: false,
        mastery: false,
        "max-haste": false,
        "max-crit": false,
        "max-vers": false,
        "max-mastery": false,
        speed: true,
        prismatic: true,
        min_ilvl: 580,
        max_ilvl: 1000,
        max_buyout: 2000,
        slots: [
            "Waist", "Legs", "Wrist", "Hands", "Back",
            "One-Hand", "Two-Hand", "Main-Hand", "Held In Off-hand", "Off-Hand", "Off Hand", "Ranged", "Ranged Right",
            "Finger", "Trinket", "Held In Off-hand"
        ],
        armor_types: ["Cloth", "Leather", "Mail", "Plate", "Miscellaneous"],
        weapon_types: [
            "Dagger", "Sword", "Axe", "Mace", "Fist Weapon", "Polearm", "Staff", "Off-Hand",
            "Warglaives", "Gun", "Bow", "Crossbow", "Thrown", "Shield", "Wand", "Off Hand", "Ranged Right"
        ]
    }
};
