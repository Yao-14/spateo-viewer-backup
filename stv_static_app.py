from stviewer.static_app import state, static_server

if __name__ == "__main__":
    # upload anndata
    state.selected_dir = None
    # host="0.0.0.0", port="8080"
    static_server.start(port="8080")
