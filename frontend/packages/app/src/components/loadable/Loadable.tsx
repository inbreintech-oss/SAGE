import React, {Suspense, type LazyExoticComponent} from "react";
import Loader from "./Loader";

/**
 * Lazy 로딩 컴포넌트
 * @param {React.LazyExoticComponent<() => React.JSX.Element>} Page 로딩할 컴포넌트
 * @constructor
 */
const Loadable = (Page: LazyExoticComponent<() => React.JSX.Element>) =>
    function LoadableElement() {
        return (
            <Suspense fallback={<Loader/>}>
                <Page/>
            </Suspense>
        )
    }

export default Loadable;
