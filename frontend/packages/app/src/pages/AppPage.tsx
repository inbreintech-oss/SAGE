import {AppLayout} from "@/layouts/app";
import {Outlet} from "react-router-dom";

export default function AppPage() {
    return (
        <AppLayout>
            <Outlet/>
        </AppLayout>
    )
}
