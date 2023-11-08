window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, latlng, context) {
            const p = feature.properties;
            if (p.type === 'circlemarker') {
                return L.circleMarker(latlng, radius = p._radius)
            }
            if (p.type === 'circle') {
                return L.circle(latlng, radius = p._mRadius)
            }
            return L.marker(latlng);
        },
        function1: function(feature, latlng, context) {
            const {
                min,
                max,
                colorscale,
                circleOptions,
                colorProp
            } = context.props.hideout;
            const csc = chroma.scale(colorscale).domain([min, max]); // chroma lib to construct colorscale
            circleOptions.fillColor = csc(feature.properties[colorProp]); // set color based on color prop.
            return L.circleMarker(latlng, circleOptions); // sender a simple circle marker.
        }
    }
});